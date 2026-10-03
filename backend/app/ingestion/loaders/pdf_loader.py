from __future__ import annotations

import json
import shutil
import socket
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import opendataloader_pdf


DEFAULT_HYBRID_URL = "http://127.0.0.1:5002"
ExtractionMode = Literal["standard", "hybrid", "auto"]


class PDFExtractionError(RuntimeError):
	pass


@dataclass
class PDFExtractionResult:
	source_file: str
	# Raw markdown from opendataloader-pdf, kept as-is (tables, headings, etc. preserved):
	# our corpus is dense with tables (barèmes, tranches d'imposition) and LLMs are trained
	# heavily on markdown, so stripping it down to plain text would lose structure for no
	# benefit downstream (chunking/embeddings/LLM all consume this field directly).
	text: str
	markdown: str
	page_count: int
	warnings: list[str] = field(default_factory=list)


def is_hybrid_server_available(hybrid_url: str = DEFAULT_HYBRID_URL) -> bool:
	"""Check whether an `opendataloader-pdf-hybrid` server is reachable at `hybrid_url`.

	This module never starts/stops that server itself: loading its OCR/layout models takes
	minutes, so the server must be started once (e.g. `opendataloader-pdf-hybrid --port 5002`)
	and reused across many PDFs, not per-call.
	"""
	try:
		host_port = hybrid_url.split("://", 1)[-1].split("/", 1)[0]
		host, _, port_str = host_port.partition(":")
		port = int(port_str) if port_str else 80
	except (ValueError, IndexError):
		return False

	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.settimeout(1)
		return sock.connect_ex((host, port)) == 0


def _run_opendataloader(
	pdf_path: Path,
	work_dir: Path,
	*,
	mode: ExtractionMode,
	hybrid_url: str,
) -> None:
	convert_kwargs: dict = {
		"input_path": str(pdf_path),
		"output_dir": str(work_dir),
		"format": "markdown,json",
		"quiet": True,
	}
	if mode == "hybrid":
		if not is_hybrid_server_available(hybrid_url):
			raise PDFExtractionError(
				f"Hybrid extraction requested but no server is reachable at {hybrid_url}. "
				"Start it first with `opendataloader-pdf-hybrid --port 5002` and keep it running "
				"across calls (it takes minutes to load its models)."
			)
		convert_kwargs.update(hybrid="docling-fast", hybrid_mode="auto", hybrid_url=hybrid_url, hybrid_fallback=True)

	try:
		opendataloader_pdf.convert(**convert_kwargs)
	except Exception as exc:
		raise PDFExtractionError(f"opendataloader-pdf failed on {pdf_path.name}: {exc}") from exc


def extract_pdf(
	pdf_path: str | Path,
	*,
	output_dir: str | Path | None = None,
	keep_output: bool = False,
	mode: ExtractionMode = "standard",
	hybrid_url: str = DEFAULT_HYBRID_URL,
) -> PDFExtractionResult:
	"""Extract text from a PDF via opendataloader-pdf.

	`mode`:
	- "standard" (default): local Java pipeline only, no OCR. Fast, but produces no text on
	  scanned/image-only PDFs (see `data/raw/pdfs/unverified_no_text/` for real examples).
	- "hybrid": forces the `docling-fast`/easyocr backend. Requires a running
	  `opendataloader-pdf-hybrid` server (see `is_hybrid_server_available`); raises otherwise.
	- "auto": tries "standard" first and only retries with "hybrid" if no text was extracted —
	  avoids paying the OCR cost on the majority of PDFs that already have native text.
	"""
	pdf_path = Path(pdf_path)
	if not pdf_path.exists():
		raise PDFExtractionError(f"PDF not found: {pdf_path}")

	work_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="opendataloader_"))
	work_dir.mkdir(parents=True, exist_ok=True)

	effective_mode: ExtractionMode = "standard" if mode == "auto" else mode
	_run_opendataloader(pdf_path, work_dir, mode=effective_mode, hybrid_url=hybrid_url)

	markdown_path = work_dir / f"{pdf_path.stem}.md"
	json_path = work_dir / f"{pdf_path.stem}.json"

	if not markdown_path.exists():
		raise PDFExtractionError(f"No markdown output produced for {pdf_path.name}")

	markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
	text = markdown

	if mode == "auto" and not text.strip():
		_run_opendataloader(pdf_path, work_dir, mode="hybrid", hybrid_url=hybrid_url)
		if markdown_path.exists():
			markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
			text = markdown
			effective_mode = "hybrid"

	warnings: list[str] = []
	page_count = 0

	if json_path.exists():
		try:
			metadata = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
			page_count = int(metadata.get("number of pages", 0))
		except (json.JSONDecodeError, ValueError, AttributeError) as exc:
			warnings.append(f"Could not parse JSON output: {exc}")

	if not text.strip():
		warnings.append(
			"Extraction produced no text (likely a scanned/image PDF requiring OCR)"
			if effective_mode == "standard"
			else "Extraction produced no text even with hybrid OCR"
		)

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
