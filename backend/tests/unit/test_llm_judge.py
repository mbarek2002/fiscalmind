from __future__ import annotations

import pytest

from backend.app.agents.simple_agent import SimpleAgentResult
from backend.app.core.config import Settings
from backend.app.evaluation import llm_judge
from backend.app.evaluation.golden_dataset_by_article import ExpectedChunk, GoldenExampleByArticle


def _settings(**overrides: object) -> Settings:
	base = {"database_url": "sqlite+aiosqlite:///./test_judge.db"}
	base.update(overrides)
	return Settings(**base)


class _FakeJudge:
	model = "fake-judge"

	def __init__(self, answers: list[dict]) -> None:
		self.answers = list(answers)
		self.prompts: list[str] = []

	def ask_json(self, prompt: str) -> dict:
		self.prompts.append(prompt)
		return self.answers.pop(0)


def test_parse_judge_json_tolerates_code_fences() -> None:
	raw = 'Voici :\n```json\n{"score": 4, "verdict": "correct", "justification": "ok"}\n```'
	assert llm_judge.parse_judge_json(raw)["score"] == 4


def test_parse_judge_json_rejects_text_without_json() -> None:
	with pytest.raises(ValueError):
		llm_judge.parse_judge_json("pas de json")


def test_resolve_judge_config_nvidia_defaults_to_nemotron() -> None:
	settings = _settings(judge_provider="nvidia", judge_model=None, nvidia_api_key="nvapi-x")
	base_url, api_key, model = llm_judge.resolve_judge_chat_config(settings)
	assert base_url == "https://integrate.api.nvidia.com/v1"
	assert api_key == "nvapi-x"
	assert model == "nvidia/nemotron-3.5-super-vl-120b-a12b"
	assert llm_judge.judge_extra_body(settings) == {"chat_template_kwargs": {"enable_thinking": False}}


def test_resolve_judge_config_local_keeps_historic_behaviour() -> None:
	settings = _settings(judge_provider="local", judge_model=None, local_llm_model_name="mistral:latest")
	assert llm_judge.resolve_judge_chat_config(settings)[2] == "mistral:latest"


def test_resolve_judge_config_requires_nvidia_key() -> None:
	with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
		llm_judge.resolve_judge_chat_config(_settings(judge_provider="nvidia", nvidia_api_key=None))


def test_run_llm_judge_scores_answerable_and_refusals(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(llm_judge, "fetch_chunk_texts", lambda ids: {"doc.pdf::chunk1": "Article 1 : taux 19 %."})
	golden = [
		GoldenExampleByArticle("Taux ?", "fr", "doc.pdf", [ExpectedChunk("doc.pdf::chunk1", 1)]),
		GoldenExampleByArticle("Hors corpus ?", "fr", None, [], is_unanswerable=True),
	]

	def fake_agent(question: str, language: str) -> SimpleAgentResult:
		return SimpleAgentResult(question=question, answer="19 %", contexts=["c"], source_ids=["doc.pdf::chunk1"])

	judge = _FakeJudge(
		[
			{"score": 5, "verdict": "correct", "justification": "ok"},
			{"refused": True, "justification": "refuse"},
		]
	)

	summary, results = llm_judge.run_llm_judge(golden, agent=fake_agent, judge=judge)

	assert len(results) == 2
	assert summary.mean_score == 5
	assert summary.correct_rate == 1.0
	assert summary.refusal_rate == 1.0
	assert summary.retrieval_hit_rate == 1.0
	assert summary.n_errors == 0
	assert "Article 1 : taux 19 %." in judge.prompts[0]


def test_run_llm_judge_records_agent_errors(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(llm_judge, "fetch_chunk_texts", lambda ids: {})
	golden = [GoldenExampleByArticle("Q", "fr", "d.pdf", [ExpectedChunk("d.pdf::chunk1", 1)])]

	def failing_agent(question: str, language: str) -> SimpleAgentResult:
		raise RuntimeError("429 rate limit")

	summary, _ = llm_judge.run_llm_judge(golden, agent=failing_agent, judge=_FakeJudge([]))

	assert summary.n_errors == 1
	assert "429" in summary.examples[0].error
