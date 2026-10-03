from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.app.agents.legal_retrieval import retrieve_legal_articles
from backend.app.agents.jurisprudence_retrieval import retrieve_jurisprudence
from backend.app.api.deps import require_roles
from backend.app.ingestion.chunking import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP_CHARS, chunk_document
from backend.app.ingestion.loaders.pdf_loader import DEFAULT_HYBRID_URL, PDFExtractionError, extract_pdf
from backend.app.models.db_models import User
from backend.app.models.enums import UserRole
from backend.app.models.schemas import (
	ChunkDebugInfo,
	ExtractChunkDebugResponse,
	RetrievedArticleDebugInfo,
	RetrievedJurisprudenceDebugInfo,
	RetrieveDebugRequest,
	RetrieveDebugResponse,
)


router = APIRouter(prefix="/debug")

UPLOAD_DIR = Path("data/raw/debug_uploads")
SUPPORTED_EXTENSIONS = {".pdf"}


@router.post("/extract-chunk", response_model=ExtractChunkDebugResponse, status_code=status.HTTP_200_OK)
async def debug_extract_and_chunk(
	file: UploadFile = File(...),
	mode: str = Form("standard"),
	hybrid_url: str = Form(DEFAULT_HYBRID_URL),
	max_chars: int = Form(DEFAULT_MAX_CHARS),
	overlap_chars: int = Form(DEFAULT_OVERLAP_CHARS),
	_: User = Depends(require_roles(UserRole.admin)),
) -> ExtractChunkDebugResponse:
	"""Dev/test-only endpoint: run a PDF through extract_pdf() + chunk_document() and return
	every intermediate value (extraction warnings, page count, each chunk's text/langue/headers)
	so the pipeline's behavior can be inspected without touching the real ingestion tables."""
	if mode not in ("standard", "hybrid", "auto"):
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="mode must be one of: standard, hybrid, auto",
		)

	suffix = Path(file.filename or "").suffix.lower()
	if suffix not in SUPPORTED_EXTENSIONS:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail=f"Unsupported file type '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
		)

	content = await file.read()
	UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
	local_path = UPLOAD_DIR / f"{uuid4()}{suffix}"
	local_path.write_bytes(content)

	try:
		result = extract_pdf(local_path, mode=mode, hybrid_url=hybrid_url)  # type: ignore[arg-type]
	except PDFExtractionError as exc:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
	finally:
		local_path.unlink(missing_ok=True)

	chunks = chunk_document(
		file.filename or local_path.name,
		result.text,
		max_chars=max_chars,
		overlap_chars=overlap_chars,
	)

	return ExtractChunkDebugResponse(
		filename=file.filename or local_path.name,
		mode_requested=mode,
		page_count=result.page_count,
		extraction_warnings=result.warnings,
		text_length=len(result.text),
		chunk_count=len(chunks),
		chunks=[
			ChunkDebugInfo(
				chunk_id=c.chunk_id,
				chunk_index=c.chunk_index,
				text=c.text,
				langue=c.langue,
				numero_article=c.numero_article,
				headers=c.headers,
				char_count=len(c.text),
			)
			for c in chunks
		],
	)


@router.post("/retrieve", response_model=RetrieveDebugResponse, status_code=status.HTTP_200_OK)
async def debug_retrieve(
	payload: RetrieveDebugRequest,
	_: User = Depends(require_roles(UserRole.admin)),
) -> RetrieveDebugResponse:
	"""Dev/test-only endpoint: run hybrid search + rerank (+ graph context) in isolation, with
	full scoring detail, without the synthesis/verification steps that /query runs afterward."""
	legal_chunks, graph_context_ids = retrieve_legal_articles(
		question=payload.question,
		language=payload.language,
		top_k=payload.top_k,
	)

	jurisprudence_chunks = []
	if payload.include_jurisprudence:
		jurisprudence_chunks = retrieve_jurisprudence(
			question=payload.question,
			language=payload.language,
			top_k=payload.top_k,
		)

	return RetrieveDebugResponse(
		question=payload.question,
		language=payload.language,
		legal_results=[
			RetrievedArticleDebugInfo(
				article_id=c.article_id,
				loi=c.loi,
				numero_article=c.numero_article,
				statut=c.statut,
				langue=c.langue,
				extrait=c.extrait,
				category=c.category,
				dense_score=c.dense_score,
				sparse_score=c.sparse_score,
				fused_score=c.fused_score,
			)
			for c in legal_chunks
		],
		jurisprudence_results=[
			RetrievedJurisprudenceDebugInfo(
				case_id=c.case_id,
				reference=c.reference,
				resume=c.resume,
				langue=c.langue,
				categorie=c.categorie,
				dense_score=c.dense_score,
				sparse_score=c.sparse_score,
				fused_score=c.fused_score,
			)
			for c in jurisprudence_chunks
		],
		graph_context_ids=graph_context_ids,
	)
