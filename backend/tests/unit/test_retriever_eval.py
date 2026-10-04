from backend.app.evaluation import retriever_eval
from backend.app.evaluation.golden_dataset import GoldenExample
from backend.app.retrieval.hybrid_search import RetrievedChunk


def _fake_chunk(article_id: str, language: str) -> RetrievedChunk:
	return RetrievedChunk(
		article_id=article_id,
		loi="loi-test.pdf",
		numero_article=0,
		statut="en_vigueur",
		langue=language,
		extrait="extrait de test",
		category="non_classe",
	)


def test_build_eval_dataframe_retrieves_chunk_ids_per_question(monkeypatch) -> None:
	def fake_retrieve_legal_candidates(question: str, language: str, top_k: int) -> list[RetrievedChunk]:
		assert top_k == 3
		return [_fake_chunk("doc::1", language), _fake_chunk("doc::2", language)]

	monkeypatch.setattr(retriever_eval, "retrieve_legal_candidates", fake_retrieve_legal_candidates)

	golden_set = [
		GoldenExample(question="Question A ?", language="fr", expected_chunk_ids=["doc::1"], anchor_text="anchor A"),
		GoldenExample(question="Question B ?", language="fr", expected_chunk_ids=["doc::3"], anchor_text="anchor B"),
	]

	eval_df = retriever_eval._build_eval_dataframe(golden_set, top_k=3)

	assert list(eval_df["questions"]) == ["Question A ?", "Question B ?"]
	assert list(eval_df["ground_truth"]) == [["doc::1"], ["doc::3"]]
	assert list(eval_df["retrieved_context"]) == [["doc::1", "doc::2"], ["doc::1", "doc::2"]]


def test_build_eval_dataframe_is_empty_for_empty_golden_set() -> None:
	eval_df = retriever_eval._build_eval_dataframe([], top_k=3)

	assert eval_df.empty
	assert list(eval_df.columns) == ["questions", "language", "ground_truth", "retrieved_context"]
