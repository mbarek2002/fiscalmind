from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import opendataloader_pdf


ARABIC_CHAR_PATTERN = re.compile(r"[؀-ۿݐ-ݿ]")
TATWEEL = "ـ"
HEADING_PREFIX = re.compile(r"^#{1,6}\s*")
TABLE_RULE_ROW = re.compile(r"^\|?[\s:|-]+\|?$")
IMAGE_MARKDOWN = re.compile(r"^!\[[^\]]*\]\([^)]*\)$")


class PDFExtractionError(RuntimeError):
	pass


@dataclass
class PDFExtractionResult:
	source_file: str
	text: str
	markdown: str
	page_count: int
	warnings: list[str] = field(default_factory=list)


def _is_mostly_arabic(token: str) -> bool:
	letters = [c for c in token if c.isalpha()]
	if not letters:
		return False
	arabic_letters = [c for c in letters if ARABIC_CHAR_PATTERN.match(c)]
	return len(arabic_letters) / len(letters) > 0.5


def _fix_rtl_line(line: str) -> str:
	"""Reverse word/char order to undo visual-order mirroring seen on some Arabic PDFs."""
	# opendataloader-pdf emits some Arabic lines in raw glyph-stream (visual) order rather
	# than logical reading order; reversing words and Arabic-majority tokens approximates a fix.
	tokens = line.split(" ")
	fixed_tokens = []
	for token in reversed(tokens):
		if _is_mostly_arabic(token):
			fixed_tokens.append(token[::-1].replace(TATWEEL, ""))
		else:
			fixed_tokens.append(token)
	return " ".join(fixed_tokens)


def _clean_markdown_line(line: str) -> str:
	stripped = line.strip()
	if not stripped:
		return ""
	if TABLE_RULE_ROW.match(stripped) or IMAGE_MARKDOWN.match(stripped):
		return ""
	stripped = HEADING_PREFIX.sub("", stripped)
	stripped = stripped.strip("|").replace("|", " ").strip()
	if ARABIC_CHAR_PATTERN.search(stripped):
		stripped = _fix_rtl_line(stripped)
	return stripped


def _markdown_to_plain_text(markdown: str) -> str:
	lines = [_clean_markdown_line(line) for line in markdown.splitlines()]
	return "\n".join(line for line in lines if line)


def extract_pdf(pdf_path: str | Path, *, output_dir: str | Path | None = None, keep_output: bool = False) -> PDFExtractionResult:
	"""Extract text from a PDF via opendataloader-pdf's local (non-hybrid) pipeline."""
	# Scanned/image-only pages yield little or no text (surfaced via `warnings`) and need
	# the --hybrid OCR mode instead; not used here to keep extraction fast on native-text PDFs.
	pdf_path = Path(pdf_path)
	if not pdf_path.exists():
		raise PDFExtractionError(f"PDF not found: {pdf_path}")

	work_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="opendataloader_"))
	work_dir.mkdir(parents=True, exist_ok=True)

	try:
		opendataloader_pdf.convert(
			input_path=str(pdf_path),
			output_dir=str(work_dir),
			format="markdown,json",
			quiet=True,
		)
	except Exception as exc:
		raise PDFExtractionError(f"opendataloader-pdf failed on {pdf_path.name}: {exc}") from exc

	markdown_path = work_dir / f"{pdf_path.stem}.md"
	json_path = work_dir / f"{pdf_path.stem}.json"

	if not markdown_path.exists():
		raise PDFExtractionError(f"No markdown output produced for {pdf_path.name}")

	markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
	warnings: list[str] = []
	page_count = 0

	if json_path.exists():
		try:
			metadata = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
			page_count = int(metadata.get("number of pages", 0))
		except (json.JSONDecodeError, ValueError, AttributeError) as exc:
			warnings.append(f"Could not parse JSON output: {exc}")

	text = _markdown_to_plain_text(markdown)
	if not text.strip():
		warnings.append("Extraction produced no text (likely a scanned/image PDF requiring OCR)")

	if not keep_output:
		shutil.rmtree(work_dir, ignore_errors=True)

	return PDFExtractionResult(
		source_file=pdf_path.name,
		text=text,
		markdown=markdown,
		page_count=page_count,
		warnings=warnings,
	)


def iter_pdf_paths(source_dir: str | Path) -> list[Path]:
	return sorted(p for p in Path(source_dir).rglob("*.pdf") if p.is_file())
