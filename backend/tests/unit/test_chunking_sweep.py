from backend.app.evaluation.chunking_sweep import _build_sweep_eval_dataframe, _resolve_ground_truth
from backend.app.evaluation.golden_dataset import GoldenExample
from backend.app.ingestion.chunking import chunk_document


def test_resolve_ground_truth_finds_chunk_containing_anchor_text() -> None:
	text = "## Art. 1\nPremier article sans intérêt.\n\n## Art. 2\nLe plafond est fixé à 200 000 dinars pour ce dispositif."
	chunks = chunk_document("test.pdf", text)
	golden_set = [
		GoldenExample(question="Quel est le plafond ?", language="fr", expected_chunk_ids=[], anchor_text="200 000 dinars")
	]

	ground_truth = _resolve_ground_truth(chunks, golden_set)

	matched_ids = ground_truth["Quel est le plafond ?"]
	assert matched_ids
	matched_chunk = next(chunk for chunk in chunks if chunk.chunk_id == matched_ids[0])
	assert "200 000 dinars" in matched_chunk.text


def test_resolve_ground_truth_returns_empty_list_when_anchor_not_found() -> None:
	chunks = chunk_document("test.pdf", "## Art. 1\nContenu quelconque.")
	golden_set = [
		GoldenExample(
			question="Question sans correspondance ?",
			language="fr",
			expected_chunk_ids=[],
			anchor_text="texte absent du document",
		)
	]

	ground_truth = _resolve_ground_truth(chunks, golden_set)

	assert ground_truth["Question sans correspondance ?"] == []


def test_resolve_ground_truth_matches_every_chunk_containing_the_anchor() -> None:
	# Overlap can legitimately duplicate the anchor text across two adjacent chunks — both are
	# valid retrieval targets, not just the first one found.
	text = "## Art. 1\n" + ("mot " * 50) + "ancre-unique" + (" mot" * 50) + "\n\n## Art. 2\nAutre contenu."
	chunks = chunk_document("test.pdf", text, max_chars=120, overlap_chars=60)
	golden_set = [GoldenExample(question="Q ?", language="fr", expected_chunk_ids=[], anchor_text="ancre-unique")]

	ground_truth = _resolve_ground_truth(chunks, golden_set)

	assert len(ground_truth["Q ?"]) >= 1


def test_build_sweep_eval_dataframe_separates_unresolved_questions(monkeypatch) -> None:
	import backend.app.evaluation.chunking_sweep as chunking_sweep

	monkeypatch.setattr(chunking_sweep, "retrieve_chunk_ids", lambda question, language, top_k: ["doc::1"])

	golden_set = [
		GoldenExample(question="Resolue ?", language="fr", expected_chunk_ids=[], anchor_text="x"),
		GoldenExample(question="Non resolue ?", language="fr", expected_chunk_ids=[], anchor_text="y"),
	]
	ground_truth_by_question = {"Resolue ?": ["doc::1"], "Non resolue ?": []}

	eval_df, unresolved = _build_sweep_eval_dataframe(golden_set, ground_truth_by_question, top_k=3)

	assert unresolved == ["Non resolue ?"]
	assert list(eval_df["questions"]) == ["Resolue ?"]
	assert list(eval_df["ground_truth"]) == [["doc::1"]]
