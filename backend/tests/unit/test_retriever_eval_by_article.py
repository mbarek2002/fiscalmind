from backend.app.evaluation import retriever_eval_by_article
from backend.app.evaluation.golden_dataset_by_article import ExpectedChunk, GoldenExampleByArticle
from backend.app.ingestion.indexing_by_article import ArticleSearchResult


def _fake_result(chunk_id: str, score: float) -> ArticleSearchResult:
	return ArticleSearchResult(id_chunk=chunk_id, source_file="test.pdf", numero_article=1, langue="fr", texte="x", score=score)


def test_build_eval_dataframe_skips_unanswerable_and_empty_expected(monkeypatch) -> None:
	def fake_search(question, language, top_k):
		return [_fake_result("doc::1", 0.9)]

	monkeypatch.setattr(retriever_eval_by_article, "search_by_article_hybrid", fake_search)

	golden_set = [
		GoldenExampleByArticle(question="Q1", language="fr", source_file="f.pdf", expected=[ExpectedChunk("doc::1", 1)]),
		GoldenExampleByArticle(question="Q2 (sans reponse)", language="fr", source_file=None, expected=[], is_unanswerable=True),
	]

	eval_df = retriever_eval_by_article._build_eval_dataframe(golden_set, top_k=5)

	assert list(eval_df["questions"]) == ["Q1"]
	assert list(eval_df["ground_truth"]) == [["doc::1"]]
	assert list(eval_df["retrieved_context"]) == [["doc::1"]]


def test_build_eval_dataframe_supports_multi_chunk_ground_truth(monkeypatch) -> None:
	def fake_search(question, language, top_k):
		return [_fake_result("doc::1", 0.9), _fake_result("doc::2", 0.8)]

	monkeypatch.setattr(retriever_eval_by_article, "search_by_article_hybrid", fake_search)

	golden_set = [
		GoldenExampleByArticle(
			question="Q multi",
			language="fr",
			source_file="f.pdf",
			expected=[ExpectedChunk("doc::1", 1), ExpectedChunk("doc::2", 2)],
		)
	]

	eval_df = retriever_eval_by_article._build_eval_dataframe(golden_set, top_k=5)

	assert eval_df.loc[0, "ground_truth"] == ["doc::1", "doc::2"]


def test_calibrate_no_answer_threshold_uses_min_of_answerable_scores(monkeypatch) -> None:
	scores = iter([0.8, 0.6, 0.9])

	monkeypatch.setattr(retriever_eval_by_article, "get_top_dense_score", lambda question, language: next(scores))

	golden_set = [
		GoldenExampleByArticle(question="Q1", language="fr", source_file="f.pdf", expected=[ExpectedChunk("doc::1", 1)]),
		GoldenExampleByArticle(question="Q2", language="fr", source_file="f.pdf", expected=[ExpectedChunk("doc::2", 2)]),
		GoldenExampleByArticle(question="Q3", language="fr", source_file="f.pdf", expected=[ExpectedChunk("doc::3", 3)]),
	]

	threshold = retriever_eval_by_article._calibrate_no_answer_threshold(golden_set)

	assert threshold == 0.6


def test_calibrate_no_answer_threshold_returns_none_without_answerable_questions() -> None:
	golden_set = [GoldenExampleByArticle(question="Sans reponse", language="fr", source_file=None, expected=[], is_unanswerable=True)]

	assert retriever_eval_by_article._calibrate_no_answer_threshold(golden_set) is None


def test_evaluate_unanswerable_counts_correct_refusals(monkeypatch) -> None:
	scores = iter([0.2, 0.9])  # 1ere question : score bas (bon refus), 2e : score haut (hallucination)

	monkeypatch.setattr(retriever_eval_by_article, "get_top_dense_score", lambda question, language: next(scores))

	golden_set = [
		GoldenExampleByArticle(question="Sans reponse 1", language="fr", source_file=None, expected=[], is_unanswerable=True),
		GoldenExampleByArticle(question="Sans reponse 2", language="fr", source_file=None, expected=[], is_unanswerable=True),
	]

	metrics = retriever_eval_by_article._evaluate_unanswerable(golden_set, threshold=0.5)

	assert metrics["unanswerable_total"] == 2
	assert metrics["unanswerable_correct_refusal_rate"] == 0.5
	assert metrics["unanswerable_calibrated_threshold"] == 0.5


def test_evaluate_unanswerable_returns_empty_dict_when_none_present() -> None:
	golden_set = [GoldenExampleByArticle(question="Q", language="fr", source_file="f.pdf", expected=[ExpectedChunk("doc::1", 1)])]

	assert retriever_eval_by_article._evaluate_unanswerable(golden_set, threshold=0.5) == {}


def test_evaluate_unanswerable_returns_empty_dict_when_threshold_is_none() -> None:
	golden_set = [GoldenExampleByArticle(question="Sans reponse", language="fr", source_file=None, expected=[], is_unanswerable=True)]

	assert retriever_eval_by_article._evaluate_unanswerable(golden_set, threshold=None) == {}
