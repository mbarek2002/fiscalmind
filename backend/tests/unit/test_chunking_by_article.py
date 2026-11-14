from backend.app.ingestion.chunking_by_article import (
	PageText,
	_build_page_index,
	_detect_boilerplate_lines,
	_normalize_article_number,
	_page_number_at,
	_strip_boilerplate,
	chunk_by_article,
)


def test_normalize_article_number_handles_digits() -> None:
	assert _normalize_article_number("23") == 23


def test_normalize_article_number_handles_premier_variants() -> None:
	assert _normalize_article_number("premier") == 1
	assert _normalize_article_number("1er") == 1
	assert _normalize_article_number("unique") == 1


def test_normalize_article_number_returns_none_for_unknown() -> None:
	assert _normalize_article_number("deuxieme") is None


def test_detect_boilerplate_lines_finds_lines_repeated_across_pages() -> None:
	pages = [
		PageText(page_number=1, text="N 67\nJournal Officiel\nContenu page 1"),
		PageText(page_number=2, text="N 67\nJournal Officiel\nContenu page 2"),
		PageText(page_number=3, text="N 67\nJournal Officiel\nContenu page 3"),
	]
	boilerplate = _detect_boilerplate_lines(pages, min_repeat_ratio=0.6)

	assert "N 67" in boilerplate
	assert "Journal Officiel" in boilerplate
	assert "Contenu page 1" not in boilerplate


def test_strip_boilerplate_removes_only_matching_lines() -> None:
	text = "N 67\nArt. 3 - Vrai contenu\nN 67"
	result = _strip_boilerplate(text, {"N 67"})

	assert result == "Art. 3 - Vrai contenu"


def test_build_page_index_tracks_offsets_per_page() -> None:
	pages = [PageText(page_number=1, text="abc"), PageText(page_number=2, text="defgh")]
	full_text, offsets = _build_page_index(pages)

	assert full_text == "abc\ndefgh"
	assert offsets == [(0, 4), (4, 10)]


def test_page_number_at_resolves_correct_page() -> None:
	pages = [PageText(page_number=1, text="abc"), PageText(page_number=2, text="defgh")]
	_, offsets = _build_page_index(pages)

	assert _page_number_at(0, pages, offsets) == 1
	assert _page_number_at(5, pages, offsets) == 2


def test_chunk_by_article_splits_one_chunk_per_article() -> None:
	pages = [PageText(page_number=1, text="Art. 1 - Premier contenu.\nArt. 2 - Deuxieme contenu.")]
	chunks = chunk_by_article("test.pdf", pages)

	assert len(chunks) == 2
	assert chunks[0].numero_article == 1
	assert "Premier contenu" in chunks[0].text
	assert chunks[1].numero_article == 2
	assert "Deuxieme contenu" in chunks[1].text


def test_chunk_by_article_keeps_preamble_as_separate_chunk() -> None:
	pages = [PageText(page_number=1, text="Preambule de la loi.\nArt. 1 - Contenu.")]
	chunks = chunk_by_article("test.pdf", pages)

	assert chunks[0].numero_article is None
	assert "Preambule" in chunks[0].text
	assert chunks[1].numero_article == 1


def test_chunk_by_article_detects_premier_1er_and_unique() -> None:
	pages = [PageText(page_number=1, text="Article premier - A.\nArt. 2 - B.\nArticle unique.")]
	chunks = chunk_by_article("test.pdf", pages)

	assert [c.numero_article for c in chunks] == [1, 2, 1]


def test_chunk_by_article_captures_bis_ter_suffix() -> None:
	pages = [PageText(page_number=1, text="Art. 44 bis - Contenu special.")]
	chunks = chunk_by_article("test.pdf", pages)

	assert chunks[0].numero_article == 44
	assert chunks[0].headers.get("article_suffix") == "bis"


def test_chunk_by_article_ignores_cross_reference_mid_sentence() -> None:
	# Regression : "l'article 5 de la presente loi" est une reference au sein d'un
	# autre article, pas un nouveau marqueur -- ne doit pas couper le chunk. C'est
	# exactement le faux positif trouve lors des tests manuels sur le vrai corpus.
	pages = [
		PageText(
			page_number=1,
			text="Art. 22 - Les entreprises au sens de l'article 5 de la presente loi beneficient de mesures.",
		)
	]
	chunks = chunk_by_article("test.pdf", pages)

	assert len(chunks) == 1
	assert chunks[0].numero_article == 22
	assert "article 5 de la presente loi" in chunks[0].text


def test_chunk_by_article_tracks_page_start_across_pages() -> None:
	pages = [
		PageText(page_number=1, text="Art. 1 - Contenu sur la page une."),
		PageText(page_number=2, text="Art. 2 - Contenu sur la page deux."),
	]
	chunks = chunk_by_article("test.pdf", pages)

	assert chunks[0].headers["page_start"] == "1"
	assert chunks[1].headers["page_start"] == "2"


def test_chunk_by_article_sets_language_and_chunk_id() -> None:
	pages = [PageText(page_number=1, text="Art. 1 - Du contenu en francais ici.")]
	chunks = chunk_by_article("loi-test.pdf", pages)

	assert chunks[0].langue == "fr"
	assert chunks[0].chunk_id == "loi-test.pdf::chunk0"
	assert chunks[0].source_file == "loi-test.pdf"


def test_chunk_by_article_returns_empty_list_for_blank_text() -> None:
	pages = [PageText(page_number=1, text="   ")]

	assert chunk_by_article("test.pdf", pages) == []


def test_chunk_by_article_falls_back_to_size_based_when_no_article_detected() -> None:
	# Regression : les Notes communes DGI commentent des articles d'autres textes
	# sans en avoir elles-memes -- aucun marqueur "Art. N"/"Article N" propre a
	# elles. Sans ce fallback, ces ~84% du corpus produiraient 0 chunk et
	# disparaitraient silencieusement de l'index.
	text = (
		"NOTE COMMUNE N 13/2009\n"
		"OBJET : Commentaire des dispositions des articles 19 a 21 de la loi "
		"n 2008-77 relatives aux avantages fiscaux. " + ("Du texte de commentaire. " * 50)
	)
	pages = [PageText(page_number=1, text=text)]

	chunks = chunk_by_article("note-commune.pdf", pages)

	assert len(chunks) > 0
	assert all(c.numero_article is None for c in chunks)
	assert all(c.headers.get("chunking_fallback") == "size_based" for c in chunks)
