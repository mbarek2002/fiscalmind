from backend.app.evaluation.golden_dataset import load_golden_set


def test_load_golden_set_returns_non_empty_examples() -> None:
	examples = load_golden_set()

	assert len(examples) >= 5
	assert all(example.question for example in examples)
	assert all(example.expected_chunk_ids for example in examples)
	assert all(example.anchor_text for example in examples)
	assert all(example.language == "fr" for example in examples)


def test_load_golden_set_chunk_ids_follow_document_chunk_format() -> None:
	examples = load_golden_set()

	for example in examples:
		for chunk_id in example.expected_chunk_ids:
			assert "::" in chunk_id
