from backend.app.ingestion.chunking import chunk_document, detect_language, split_into_articles


def test_detect_language_french() -> None:
	assert detect_language("Article premier. Les dispositions suivantes sont applicables.") == "fr"


def test_detect_language_arabic() -> None:
	assert detect_language("الفصل الأول يتعلق هذا القانون بتنظيم الميزانية") == "ar"


def test_split_into_articles_french() -> None:
	text = "Preambule general.\nArticle 1\nContenu du premier article.\nArticle 2\nContenu du second article."
	segments = split_into_articles(text)

	assert [number for number, _ in segments] == [None, 1, 2]
	assert "premier article" in segments[1][1]
	assert "second article" in segments[2][1]


def test_split_into_articles_without_markers_returns_single_segment() -> None:
	text = "Un texte sans marqueur d'article identifiable."
	assert split_into_articles(text) == [(None, text)]


def test_chunk_document_splits_long_article_with_overlap() -> None:
	long_article = "Article 5\n" + ("mot " * 500)
	chunks = chunk_document("test.pdf", long_article, max_chars=200, overlap_chars=20)

	assert len(chunks) > 1
	assert all(chunk.numero_article == 5 for chunk in chunks)
	assert all(len(chunk.text) <= 200 for chunk in chunks)
	assert all(chunk.chunk_id == f"test.pdf::chunk{chunk.chunk_index}" for chunk in chunks)


def test_chunk_document_empty_text_returns_no_chunks() -> None:
	assert chunk_document("test.pdf", "   ") == []
