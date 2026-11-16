"""Evaluation LLM-as-judge de l'agent simple (pipeline par article).

Pour chaque question du golden set :
- avec reponse : le juge compare la reponse de l'agent au texte des articles
  attendus (recuperes dans Qdrant) -> note 1-5 + verdict + justification ;
- sans reponse (is_unanswerable) : le juge verifie que l'agent refuse de
  repondre au lieu d'inventer.

Le juge est un modele distinct du generateur (JUDGE_PROVIDER / JUDGE_MODEL)
pour limiter l'auto-complaisance, avec une temperature de 0.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Callable

from backend.app.agents.simple_agent import SimpleAgentResult, answer_question
from backend.app.core.config import Settings, get_settings
from backend.app.evaluation.golden_dataset_by_article import GoldenExampleByArticle, load_golden_set
from backend.app.ingestion.indexing_by_article import fetch_chunk_texts

DEFAULT_JUDGE_MODELS = {
	# meta/llama-3.3-70b-instruct a ete retire par NVIDIA le 2026-08-26.
	"nvidia": "nvidia/nemotron-3.5-super-vl-120b-a12b",
	"openai": "gpt-4o-mini",
}

CORRECTNESS_PROMPT = """Tu es un evaluateur expert en fiscalite tunisienne.
On te donne une QUESTION, le TEXTE DE REFERENCE (article(s) de loi qui contiennent la bonne reponse)
et la REPONSE d'un assistant. Juge si la REPONSE est correcte PAR RAPPORT AU TEXTE DE REFERENCE.

Bareme :
5 = correcte et complete ; 4 = correcte, detail mineur manquant ;
3 = partiellement correcte (element important manquant ou imprecis) ;
2 = majoritairement incorrecte ou hors sujet ; 1 = fausse, inventee, ou refus alors que la reference repond.

QUESTION :
{question}

TEXTE DE REFERENCE :
{reference}

REPONSE DE L'ASSISTANT :
{answer}

Reponds UNIQUEMENT avec un objet JSON, sans texte autour :
{{"score": <entier 1-5>, "verdict": "correct" | "partiel" | "incorrect", "justification": "<une ou deux phrases>"}}"""

REFUSAL_PROMPT = """Tu es un evaluateur. La QUESTION ci-dessous n'a PAS de reponse dans le corpus juridique
de l'assistant. Le bon comportement est de dire clairement qu'il ne peut pas repondre a partir de ses sources,
sans inventer de reponse.

QUESTION :
{question}

REPONSE DE L'ASSISTANT :
{answer}

Reponds UNIQUEMENT avec un objet JSON, sans texte autour :
{{"refused": true | false, "justification": "<une phrase>"}}"""


@dataclass
class JudgedExample:
	question: str
	is_unanswerable: bool
	answer: str
	expected_chunk_ids: list[str]
	retrieved_chunk_ids: list[str]
	expected_retrieved: bool | None
	score: int | None = None
	verdict: str | None = None
	refused: bool | None = None
	justification: str = ""
	agent_seconds: float = 0.0
	error: str | None = None


@dataclass
class JudgeSummary:
	n_answerable: int
	n_unanswerable: int
	mean_score: float | None
	correct_rate: float | None
	partial_rate: float | None
	incorrect_rate: float | None
	refusal_rate: float | None
	retrieval_hit_rate: float | None
	mean_agent_seconds: float | None
	n_errors: int
	examples: list[JudgedExample] = field(default_factory=list)


def resolve_judge_chat_config(settings: Settings) -> tuple[str | None, str, str]:
	"""(base_url, api_key, model) du juge selon judge_provider."""
	provider = (settings.judge_provider or "local").strip().lower()
	if provider == "nvidia":
		if not settings.nvidia_api_key:
			raise RuntimeError("NVIDIA_API_KEY is required when judge_provider=nvidia")
		return settings.nvidia_base_url, settings.nvidia_api_key, settings.judge_model or DEFAULT_JUDGE_MODELS["nvidia"]
	if provider == "openai":
		if not settings.openai_api_key:
			raise RuntimeError("OPENAI_API_KEY is required when judge_provider=openai")
		return settings.openai_base_url, settings.openai_api_key, settings.judge_model or DEFAULT_JUDGE_MODELS["openai"]
	if provider == "local":
		return settings.local_llm_base_url, settings.local_llm_api_key, settings.judge_model or settings.local_llm_model_name
	raise ValueError(f"judge_provider must be one of: local, openai, nvidia (got {provider!r})")


def judge_extra_body(settings: Settings) -> dict | None:
	"""NVIDIA : coupe le mode "reflexion" (Nemotron) -- sinon le raisonnement
	consomme les tokens et la reponse JSON peut arriver vide."""
	if (settings.judge_provider or "").strip().lower() == "nvidia":
		return {"chat_template_kwargs": {"enable_thinking": False}}
	return None


def parse_judge_json(raw: str) -> dict:
	"""Extrait le premier objet JSON de la sortie du juge (tolere ```json ...```)."""
	# raw_decode lit le PREMIER objet JSON et ignore le texte qui suit (le juge
	# ajoute parfois une explication apres le JSON -> "Extra data").
	start = (raw or "").find("{")
	if start < 0:
		raise ValueError(f"no JSON object in judge output: {(raw or '')[:200]!r}")
	obj, _ = json.JSONDecoder().raw_decode(raw[start:])
	return obj


class JudgeClient:
	def __init__(self, settings: Settings | None = None, max_retries: int = 4) -> None:
		from openai import OpenAI

		settings = settings or get_settings()
		base_url, api_key, model = resolve_judge_chat_config(settings)
		self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=120)
		self.model = model
		self._extra_body = judge_extra_body(settings)
		self._max_retries = max_retries

	def ask_json(self, prompt: str) -> dict:
		last_exc: Exception | None = None
		for attempt in range(self._max_retries):
			try:
				response = self._client.chat.completions.create(
					model=self.model,
					messages=[{"role": "user", "content": prompt}],
					temperature=0.0,
					max_tokens=400,
					**({"extra_body": self._extra_body} if self._extra_body else {}),
				)
				return parse_judge_json(response.choices[0].message.content or "")
			except Exception as exc:  # limite de debit, JSON invalide, reseau...
				last_exc = exc
				time.sleep(2 * (attempt + 1))
		raise RuntimeError(f"judge failed after {self._max_retries} attempts: {last_exc!r}")


def judge_example(
	example: GoldenExampleByArticle,
	result: SimpleAgentResult,
	reference_texts: dict[str, str],
	judge: JudgeClient,
) -> JudgedExample:
	expected_ids = [e.chunk_id for e in example.expected]
	judged = JudgedExample(
		question=example.question,
		is_unanswerable=example.is_unanswerable,
		answer=result.answer,
		expected_chunk_ids=expected_ids,
		retrieved_chunk_ids=list(result.source_ids),
		expected_retrieved=(any(c in result.source_ids for c in expected_ids) if expected_ids else None),
	)
	try:
		if example.is_unanswerable:
			verdict = judge.ask_json(REFUSAL_PROMPT.format(question=example.question, answer=result.answer))
			judged.refused = bool(verdict.get("refused"))
		else:
			reference = "\n\n---\n\n".join(reference_texts.get(c, "") for c in expected_ids)
			verdict = judge.ask_json(
				CORRECTNESS_PROMPT.format(question=example.question, reference=reference, answer=result.answer)
			)
			judged.score = int(verdict.get("score"))
			judged.verdict = str(verdict.get("verdict", "")).lower()
		judged.justification = str(verdict.get("justification", ""))
	except Exception as exc:
		judged.error = repr(exc)
	return judged


def _rate(values: list[bool]) -> float | None:
	return sum(values) / len(values) if values else None


def summarize(examples: list[JudgedExample]) -> JudgeSummary:
	answerable = [e for e in examples if not e.is_unanswerable and e.error is None]
	unanswerable = [e for e in examples if e.is_unanswerable and e.error is None]
	scores = [e.score for e in answerable if e.score is not None]
	hits = [e.expected_retrieved for e in examples if e.expected_retrieved is not None]
	seconds = [e.agent_seconds for e in examples]
	return JudgeSummary(
		n_answerable=len(answerable),
		n_unanswerable=len(unanswerable),
		mean_score=(sum(scores) / len(scores)) if scores else None,
		correct_rate=_rate([e.verdict == "correct" for e in answerable]),
		partial_rate=_rate([e.verdict == "partiel" for e in answerable]),
		incorrect_rate=_rate([e.verdict == "incorrect" for e in answerable]),
		refusal_rate=_rate([bool(e.refused) for e in unanswerable]),
		retrieval_hit_rate=_rate(hits),
		mean_agent_seconds=(sum(seconds) / len(seconds)) if seconds else None,
		n_errors=sum(1 for e in examples if e.error is not None),
		examples=examples,
	)


def run_llm_judge(
	golden_set: list[GoldenExampleByArticle] | None = None,
	agent: Callable[..., SimpleAgentResult] = answer_question,
	judge: JudgeClient | None = None,
	on_progress: Callable[[int, int, JudgedExample], None] | None = None,
) -> tuple[JudgeSummary, list[SimpleAgentResult]]:
	examples = golden_set if golden_set is not None else load_golden_set()
	judge = judge or JudgeClient()
	reference_texts = fetch_chunk_texts(sorted({e.chunk_id for ex in examples for e in ex.expected}))

	judged: list[JudgedExample] = []
	agent_results: list[SimpleAgentResult] = []
	for i, example in enumerate(examples, start=1):
		start = time.time()
		try:
			result = agent(example.question, language=example.language)
			agent_seconds = time.time() - start
		except Exception as exc:
			agent_seconds = time.time() - start
			result = SimpleAgentResult(question=example.question, answer="", contexts=[])
			item = JudgedExample(
				question=example.question,
				is_unanswerable=example.is_unanswerable,
				answer="",
				expected_chunk_ids=[e.chunk_id for e in example.expected],
				retrieved_chunk_ids=[],
				expected_retrieved=None,
				error=f"agent: {exc!r}",
			)
		else:
			item = judge_example(example, result, reference_texts, judge)
		item.agent_seconds = round(agent_seconds, 2)
		agent_results.append(result)
		judged.append(item)
		if on_progress:
			on_progress(i, len(examples), item)

	return summarize(judged), agent_results


def summary_to_dict(summary: JudgeSummary) -> dict:
	return asdict(summary)
