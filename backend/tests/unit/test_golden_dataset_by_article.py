from backend.app.evaluation.golden_dataset_by_article import load_golden_set


def test_load_golden_set_returns_non_empty_examples() -> None:
	examples = load_golden_set()

	assert len(examples) >= 10
	assert all(example.question for example in examples)


def test_load_golden_set_separates_answerable_and_unanswerable() -> None:
	examples = load_golden_set()

	answerable = [e for e in examples if not e.is_unanswerable]
	unanswerable = [e for e in examples if e.is_unanswerable]

	assert len(answerable) > 0
	assert len(unanswerable) > 0
	assert all(e.expected for e in answerable)
	assert all(not e.expected for e in unanswerable)


def test_load_golden_set_supports_multi_chunk_expectations() -> None:
	examples = load_golden_set()

	multi_chunk = [e for e in examples if len(e.expected) > 1]
	assert len(multi_chunk) > 0
