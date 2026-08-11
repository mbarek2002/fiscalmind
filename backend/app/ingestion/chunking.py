from __future__ import annotations

import re
from dataclasses import dataclass


ARTICLE_MARKER_FR = re.compile(r"(?m)^\s*Article\s+(?:premier|\d+)\b", re.IGNORECASE)
ARTICLE_MARKER_AR = re.compile(r"(?m)^\s*الفصل(?:\s+عدد)?\s*\d*")
ARABIC_CHAR_PATTERN = re.compile(r"[؀-ۿݐ-ݿ]")

DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP_CHARS = 150


@dataclass
class Chunk:
	chunk_id: str
	source_file: str
	chunk_index: int
	text: str
	langue: str
	numero_article: int | None = None


def detect_language(text: str) -> str:
	sample = text[:2000]
	letters = [c for c in sample if c.isalpha()]
	if not letters:
		return "fr"
	arabic_letters = [c for c in letters if ARABIC_CHAR_PATTERN.match(c)]
	return "ar" if len(arabic_letters) / len(letters) > 0.5 else "fr"


def _find_article_boundaries(text: str) -> list[tuple[int, int | None]]:
	boundaries: list[tuple[int, int | None]] = []
	for pattern in (ARTICLE_MARKER_FR, ARTICLE_MARKER_AR):
		for match in pattern.finditer(text):
			number_match = re.search(r"\d+", match.group())
			number = int(number_match.group()) if number_match else None
			boundaries.append((match.start(), number))
	boundaries.sort(key=lambda item: item[0])
	return boundaries


def split_into_articles(text: str) -> list[tuple[int | None, str]]:
	"""Split on 'Article N' / 'الفصل N' markers; a single segment if none are found."""
	boundaries = _find_article_boundaries(text)
	if not boundaries:
		return [(None, text)]

	segments: list[tuple[int | None, str]] = []
	preamble = text[: boundaries[0][0]].strip()
	if preamble:
		segments.append((None, preamble))

	for index, (start, number) in enumerate(boundaries):
		end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(text)
		segment_text = text[start:end].strip()
		if segment_text:
			segments.append((number, segment_text))

	return segments


def _sliding_window(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
	if len(text) <= max_chars:
		return [text] if text else []

	windows: list[str] = []
	start = 0
	while start < len(text):
		end = min(start + max_chars, len(text))
		if end < len(text):
			boundary = text.rfind(" ", start, end)
			if boundary > start:
				end = boundary
		window = text[start:end].strip()
		if window:
			windows.append(window)
		if end >= len(text):
			break
		start = max(end - overlap_chars, start + 1)

	return windows


def chunk_document(
	source_file: str,
	text: str,
	*,
	max_chars: int = DEFAULT_MAX_CHARS,
	overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
	if not text.strip():
		return []

	langue = detect_language(text)
	chunks: list[Chunk] = []
	chunk_index = 0

	for numero_article, segment_text in split_into_articles(text):
		for window in _sliding_window(segment_text, max_chars=max_chars, overlap_chars=overlap_chars):
			chunks.append(
				Chunk(
					chunk_id=f"{source_file}::chunk{chunk_index}",
					source_file=source_file,
					chunk_index=chunk_index,
					text=window,
					langue=langue,
					numero_article=numero_article,
				)
			)
			chunk_index += 1

	return chunks
