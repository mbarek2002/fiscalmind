from __future__ import annotations

import sys
import types

# Shim : langchain_community >=0.4 a retire chat_models.vertexai, mais ragas
# l'importe sans garde-fou au niveau module (jamais instancie ici -- ce projet
# utilise Ollama, pas Vertex AI). Doit s'executer AVANT tout "import ragas".
try:
	import langchain_community.chat_models.vertexai  # noqa: F401
except ModuleNotFoundError:
	_stub = types.ModuleType("langchain_community.chat_models.vertexai")

	class _ChatVertexAIStub:
		def __init__(self, *args, **kwargs):
			raise RuntimeError("ChatVertexAI stub : Vertex AI n'est pas utilise dans ce projet (Ollama uniquement)")

	_stub.ChatVertexAI = _ChatVertexAIStub
	sys.modules["langchain_community.chat_models.vertexai"] = _stub

from datasets import Dataset
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, Faithfulness

from backend.app.agents.simple_agent import SimpleAgentResult, answer_question
from backend.app.core.config import get_settings
from backend.app.evaluation.golden_dataset_by_article import GoldenExampleByArticle, load_golden_set
from backend.app.ingestion.embedding_e5 import embed_passages, embed_query


class E5LangchainEmbeddings(Embeddings):
	"""Adapte embed_query()/embed_passages() (E5, deja utilise par le pipeline
	by-article -- backend/app/ingestion/embedding_e5.py) a l'interface LangChain
	Embeddings attendue par RAGAS pour AnswerRelevancy."""

	def embed_documents(self, texts: list[str]) -> list[list[float]]:
		return embed_passages(texts)

	def embed_query(self, text: str) -> list[float]:
		return embed_query(text)


def build_ragas_dataset(golden_set: list[GoldenExampleByArticle]) -> tuple[Dataset, list[SimpleAgentResult]]:
	"""Fait tourner l'agent simple (retrieve + generate, sans qualify/rerank/
	verify) sur chaque question du golden set AVEC reponse connue -- les
	questions is_unanswerable n'ont pas de sens pour Faithfulness/AnswerRelevancy
	(rien a verifier contre une absence volontaire de contexte)."""
	agent_results: list[SimpleAgentResult] = []
	for example in golden_set:
		if example.is_unanswerable:
			continue
		agent_results.append(answer_question(example.question, language=example.language))

	dataset = Dataset.from_dict(
		{
			"user_input": [r.question for r in agent_results],
			"response": [r.answer for r in agent_results],
			"retrieved_contexts": [r.contexts for r in agent_results],
		}
	)
	return dataset, agent_results


def run_ragas_evaluation(golden_set: list[GoldenExampleByArticle] | None = None):
	settings = get_settings()
	examples = golden_set if golden_set is not None else load_golden_set()
	dataset, agent_results = build_ragas_dataset(examples)

	judge_llm = LangchainLLMWrapper(
		ChatOpenAI(
			base_url=settings.local_llm_base_url,
			api_key=settings.local_llm_api_key,
			model=settings.local_llm_model_name,
			temperature=0.0,
		)
	)
	judge_embeddings = LangchainEmbeddingsWrapper(E5LangchainEmbeddings())

	result = evaluate(
		dataset=dataset,
		metrics=[Faithfulness(), AnswerRelevancy()],
		llm=judge_llm,
		embeddings=judge_embeddings,
	)
	return result, agent_results
