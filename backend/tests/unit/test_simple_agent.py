from backend.app.agents import simple_agent
from backend.app.ingestion.indexing_by_article import ArticleSearchResult


class _FakeLLMClient:
	def __init__(self, response: str) -> None:
		self._response = response

	def generate(self, prompt: str, system_prompt: str | None = None) -> str:
		return self._response


def test_answer_question_returns_answer_and_raw_contexts(monkeypatch) -> None:
	def fake_search(question, language, top_k):
		return [
			ArticleSearchResult(id_chunk="f.pdf::0", source_file="f.pdf", numero_article=3, langue="fr", texte="Texte article 3.", score=0.9),
			ArticleSearchResult(id_chunk="f.pdf::1", source_file="f.pdf", numero_article=4, langue="fr", texte="Texte article 4.", score=0.8),
		]

	monkeypatch.setattr(simple_agent, "search_by_article_hybrid", fake_search)
	monkeypatch.setattr(simple_agent, "get_llm_client", lambda: _FakeLLMClient("Reponse generee."))

	result = simple_agent.answer_question("Question test ?", language="fr", top_k=5)

	assert result.question == "Question test ?"
	assert result.answer == "Reponse generee."
	assert result.contexts == ["Texte article 3.", "Texte article 4."]


def test_answer_question_handles_no_retrieved_context(monkeypatch) -> None:
	monkeypatch.setattr(simple_agent, "search_by_article_hybrid", lambda question, language, top_k: [])
	monkeypatch.setattr(simple_agent, "get_llm_client", lambda: _FakeLLMClient("Je ne sais pas."))

	result = simple_agent.answer_question("Question sans reponse ?", language="fr")

	assert result.contexts == []
	assert result.answer == "Je ne sais pas."
