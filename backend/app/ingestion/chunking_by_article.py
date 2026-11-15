from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import pymupdf as fitz

from backend.app.ingestion.chunking import Chunk, chunk_document, detect_language

# Valide empiriquement sur les 616 fichiers du corpus francais : couvre "Art. N"
# (abrege), "Article N" / "ARTICLE N" (complet), "premier"/"1er" et "unique".
# N'accepte le marqueur qu'en tout debut de texte ou juste apres une ponctuation
# de fin de phrase (., :, !, ?) -- pas en milieu de phrase -- pour eviter les faux
# positifs du type "...au sens de l'article 5 de la presente loi..." (une reference
# croisee, pas un nouvel article) qu'un simple "debut de ligne" laissait passer.
ARTICLE_PATTERN = re.compile(
	r"(?:^|(?<=[.:!?]\s)|(?<=[.:!?]\n))\s*#{0,6}\s*Art(?:icle)?\.?\s+(\d+|premier|1er|unique)\b\.?\s*(bis|ter|quater)?",
	re.IGNORECASE,
)


@dataclass
class PageText:
	page_number: int  # 1-indexe
	text: str


def _detect_boilerplate_lines(pages: list[PageText], min_repeat_ratio: float = 0.6) -> set[str]:
	"""Identifie les lignes (en-tetes/pieds de page) qui apparaissent sur au moins
	min_repeat_ratio des pages -- un vrai contenu d'article ne se repete jamais a
	l'identique d'une page a l'autre, un en-tete/pied de page si."""
	line_page_counts: Counter[str] = Counter()
	for page in pages:
		lines_on_this_page = {line.strip() for line in page.text.splitlines() if line.strip()}
		for line in lines_on_this_page:
			line_page_counts[line] += 1

	threshold = max(2, int(len(pages) * min_repeat_ratio))
	return {line for line, count in line_page_counts.items() if count >= threshold}


def _strip_boilerplate(text: str, boilerplate: set[str]) -> str:
	kept_lines = [line for line in text.splitlines() if line.strip() not in boilerplate]
	return "\n".join(kept_lines)


def extract_pdf_pages(pdf_path: str) -> list[PageText]:
	doc = fitz.open(pdf_path)
	raw_pages = [PageText(page_number=i + 1, text=page.get_text()) for i, page in enumerate(doc)]
	doc.close()

	boilerplate = _detect_boilerplate_lines(raw_pages)
	return [PageText(page_number=p.page_number, text=_strip_boilerplate(p.text, boilerplate)) for p in raw_pages]


def _normalize_article_number(raw: str) -> int | None:
	raw = raw.lower().strip()
	if raw in ("premier", "1er", "unique"):
		return 1
	if raw.isdigit():
		return int(raw)
	return None


def _build_page_index(pages: list[PageText]) -> tuple[str, list[tuple[int, int]]]:
	"""Concatene le texte de toutes les pages et retourne, pour chaque page, la
	plage (debut, fin) dans le texte concatene -- pour retrouver le numero de
	page a partir de la position d'un match regex."""
	parts: list[str] = []
	offsets: list[tuple[int, int]] = []
	cursor = 0
	for page in pages:
		start = cursor
		parts.append(page.text)
		cursor += len(page.text) + 1  # +1 pour le separateur "\n" ajoute plus bas
		offsets.append((start, cursor))
	return "\n".join(parts), offsets


def _page_number_at(offset: int, pages: list[PageText], page_offsets: list[tuple[int, int]]) -> int:
	for page, (start, end) in zip(pages, page_offsets):
		if start <= offset < end:
			return page.page_number
	return pages[-1].page_number if pages else 1


def chunk_by_article(source_file: str, pages: list[PageText]) -> list[Chunk]:
	"""Alternative a chunk_document() (chunking.py, inchange) : un chunk = un
	article de loi, detecte par regex, au lieu d'un decoupage par taille fixe.

	Si aucun marqueur d'article n'est detecte -- ex: les Notes communes DGI, qui
	commentent des articles d'autres textes sans en avoir elles-memes (confirme
	empiriquement : ~84% des fichiers du corpus francais) -- retombe sur
	chunk_document() (decoupage par taille) plutot que de perdre silencieusement
	le document entier. Les chunks de secours sont marques via
	headers["chunking_fallback"] pour rester tracables."""
	full_text, page_offsets = _build_page_index(pages)
	if not full_text.strip():
		return []

	langue = detect_language(full_text)
	matches = list(ARTICLE_PATTERN.finditer(full_text))

	if not matches:
		fallback_chunks = chunk_document(source_file, full_text)
		for chunk in fallback_chunks:
			chunk.headers = {**chunk.headers, "chunking_fallback": "size_based"}
		return fallback_chunks

	chunks: list[Chunk] = []

	# Texte avant le premier article detecte (preambule/en-tete de loi) -- garde
	# comme chunk a part plutot que perdu, avec numero_article=None.
	preamble = full_text[: matches[0].start()].strip()
	if preamble:
		chunks.append(
			Chunk(
				chunk_id=f"{source_file}::chunk0",
				source_file=source_file,
				chunk_index=0,
				text=preamble,
				langue=langue,
				numero_article=None,
				headers={"page_start": str(_page_number_at(0, pages, page_offsets))},
			)
		)

	for i, match in enumerate(matches):
		start = match.start()
		end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
		chunk_text = full_text[start:end].strip()
		if not chunk_text:
			continue

		headers = {"page_start": str(_page_number_at(start, pages, page_offsets))}
		suffix = match.group(2).lower() if match.group(2) else None
		if suffix:
			headers["article_suffix"] = suffix

		chunks.append(
			Chunk(
				chunk_id=f"{source_file}::chunk{len(chunks)}",
				source_file=source_file,
				chunk_index=len(chunks),
				text=chunk_text,
				langue=langue,
				numero_article=_normalize_article_number(match.group(1)),
				headers=headers,
			)
		)

	return chunks
