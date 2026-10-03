from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


ARABIC_CHAR_PATTERN = re.compile(r"[؀-ۿݐ-ݿ]")

DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP_CHARS = 150

# Legal-article-boundary precision (Article N / الفصل N not always matching these generic
# markdown header levels) is deliberately out of scope here — deferred to a later LLM pass
# over the chunked text, not handled during chunking itself.
HEADERS_TO_SPLIT_ON = [("#", "H1"), ("##", "H2"), ("###", "H3"), ("####", "H4")]


@dataclass
class Chunk:
	chunk_id: str
	source_file: str
	chunk_index: int
	text: str
	langue: str
	numero_article: int | None = None
	# Header hierarchy above this chunk, e.g. {"H1": "TITRE III", "H4": "Article 81"} — as
	# produced by MarkdownHeaderTextSplitter's metadata, otherwise discarded.
	headers: dict[str, str] = field(default_factory=dict)


def detect_language(text: str) -> str:
	sample = text[:2000]
	letters = [c for c in sample if c.isalpha()]
	if not letters:
		return "fr"
	arabic_letters = [c for c in letters if ARABIC_CHAR_PATTERN.match(c)]
	return "ar" if len(arabic_letters) / len(letters) > 0.5 else "fr"


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

	header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT_ON, strip_headers=False)
	sections = header_splitter.split_text(text)

	recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=max_chars, chunk_overlap=overlap_chars)

	chunks: list[Chunk] = []
	chunk_index = 0
	for section in sections:
		for window in recursive_splitter.split_text(section.page_content):
			if not window.strip():
				continue
			chunks.append(
				Chunk(
					chunk_id=f"{source_file}::chunk{chunk_index}",
					source_file=source_file,
					chunk_index=chunk_index,
					text=window,
					langue=langue,
					headers=dict(section.metadata),
				)
			)
			chunk_index += 1

	return chunks
