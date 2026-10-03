from backend.app.ingestion.chunking import chunk_document, detect_language


def test_detect_language_french() -> None:
	assert detect_language("Article premier. Les dispositions suivantes sont applicables.") == "fr"


def test_detect_language_arabic() -> None:
	assert detect_language("الفصل الأول يتعلق هذا القانون بتنظيم الميزانية") == "ar"


def test_chunk_document_splits_by_markdown_header() -> None:
	text = "## Section A\ncontenu A\n\n## Section B\ncontenu B"
	chunks = chunk_document("test.pdf", text)

	assert len(chunks) == 2
	assert "Section A" in chunks[0].text
	assert "Section B" in chunks[1].text


def test_chunk_document_splits_long_text_with_overlap() -> None:
	long_text = "mot " * 500
	chunks = chunk_document("test.pdf", long_text, max_chars=200, overlap_chars=20)

	assert len(chunks) > 1
	assert all(chunk.numero_article is None for chunk in chunks)
	assert all(len(chunk.text) <= 200 for chunk in chunks)
	assert all(chunk.chunk_id == f"test.pdf::chunk{chunk.chunk_index}" for chunk in chunks)


def test_chunk_document_empty_text_returns_no_chunks() -> None:
	assert chunk_document("test.pdf", "   ") == []
