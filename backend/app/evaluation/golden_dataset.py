from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_GOLDEN_SET_PATH = Path(__file__).parent / "golden_sets" / "retrieval_v1.json"


@dataclass
class GoldenExample:
	question: str
	language: str
	expected_chunk_ids: list[str]
	# Exact substring guaranteed present in the expected chunk's original text. expected_chunk_ids
	# is only valid for the chunking config that produced it today (chunk boundaries — and
	# therefore chunk_index/chunk_id — shift when max_chars/overlap_chars change); anchor_text lets
	# a chunking-parameter sweep (chunking_sweep.py) re-resolve ground truth against any re-chunked
	# variant instead of only matching the one config these ids were captured from.
	anchor_text: str
	notes: str = ""


def load_golden_set(path: Path = DEFAULT_GOLDEN_SET_PATH) -> list[GoldenExample]:
	raw_entries = json.loads(path.read_text(encoding="utf-8"))
	return [
		GoldenExample(
			question=entry["question"],
			language=entry.get("language", "fr"),
			expected_chunk_ids=entry["expected_chunk_ids"],
			anchor_text=entry["anchor_text"],
			notes=entry.get("notes", ""),
		)
		for entry in raw_entries
	]
