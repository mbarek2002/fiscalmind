from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_GOLDEN_SET_PATH = Path(__file__).parent / "golden_sets" / "retrieval_by_article_v1.json"


@dataclass
class ExpectedChunk:
	chunk_id: str
	numero_article: int | None


@dataclass
class GoldenExampleByArticle:
	question: str
	language: str
	source_file: str | None
	expected: list[ExpectedChunk]
	is_unanswerable: bool = False
	notes: str = ""


def load_golden_set(path: Path = DEFAULT_GOLDEN_SET_PATH) -> list[GoldenExampleByArticle]:
	raw_entries = json.loads(path.read_text(encoding="utf-8"))
	return [
		GoldenExampleByArticle(
			question=entry["question"],
			language=entry.get("language", "fr"),
			source_file=entry.get("source_file"),
			expected=[
				ExpectedChunk(chunk_id=e["chunk_id"], numero_article=e.get("numero_article"))
				for e in entry.get("expected", [])
			],
			is_unanswerable=entry.get("is_unanswerable", False),
			notes=entry.get("notes", ""),
		)
		for entry in raw_entries
	]
