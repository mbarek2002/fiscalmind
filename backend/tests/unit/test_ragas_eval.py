from backend.app.agents.simple_agent import SimpleAgentResult
from backend.app.evaluation import ragas_eval
from backend.app.evaluation.golden_dataset_by_article import ExpectedChunk, GoldenExampleByArticle


def test_build_ragas_dataset_skips_unanswerable_questions(monkeypatch) -> None:
	def fake_answer_question(question, language):
		return SimpleAgentResult(question=question, answer="Reponse.", contexts=["Contexte."])

	monkeypatch.setattr(ragas_eval, "answer_question", fake_answer_question)

	golden_set = [
		GoldenExampleByArticle(question="Q1", language="fr", source_file="f.pdf", expected=[ExpectedChunk("doc::1", 1)]),
		GoldenExampleByArticle(question="Sans reponse", language="fr", source_file=None, expected=[], is_unanswerable=True),
	]

	dataset, agent_results = ragas_eval.build_ragas_dataset(golden_set)

	assert len(agent_results) == 1
	assert dataset["user_input"] == ["Q1"]
	assert dataset["response"] == ["Reponse."]
	assert dataset["retrieved_contexts"] == [["Contexte."]]


def test_e5_langchain_embeddings_delegates_to_e5_functions(monkeypatch) -> None:
	monkeypatch.setattr(ragas_eval, "embed_query", lambda text: [0.1, 0.2])
	monkeypatch.setattr(ragas_eval, "embed_passages", lambda texts: [[0.3, 0.4] for _ in texts])

	wrapper = ragas_eval.E5LangchainEmbeddings()

	assert wrapper.embed_query("question") == [0.1, 0.2]
	assert wrapper.embed_documents(["a", "b"]) == [[0.3, 0.4], [0.3, 0.4]]
