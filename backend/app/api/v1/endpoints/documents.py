from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_db, require_roles
from backend.app.ingestion.chunking import chunk_document
from backend.app.ingestion.loaders.pdf_loader import PDFExtractionError, extract_pdf
from backend.app.ingestion.pipeline import index_chunk_in_qdrant
from backend.app.models.db_models import DocumentMetadata, User
from backend.app.models.enums import DocumentSourceType, DocumentStatus, IngestionStatus, UserRole
from backend.app.models.schemas import DocumentPublic


router = APIRouter(prefix="/documents")

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
UPLOAD_DIR = Path("data/raw/uploads")


def _to_document_public(doc: DocumentMetadata) -> DocumentPublic:
	return DocumentPublic(
		id=doc.id,
		filename=doc.original_filename,
		size_bytes=doc.size_bytes,
		status=doc.ingestion_status,
		chunks=doc.chunk_count,
		uploaded_at=doc.created_at,
		error=doc.ingestion_error,
	)


def _extract_text(path: Path, suffix: str) -> str:
	if suffix == ".pdf":
		try:
			return extract_pdf(path).text
		except PDFExtractionError as exc:
			raise ValueError(str(exc)) from exc
	return path.read_text(encoding="utf-8", errors="ignore")


@router.get("", response_model=list[DocumentPublic])
async def list_documents(
	db: AsyncSession = Depends(get_db),
	_: User = Depends(require_roles(UserRole.admin)),
) -> list[DocumentPublic]:
	result = await db.execute(select(DocumentMetadata).order_by(DocumentMetadata.created_at.desc()))
	return [_to_document_public(doc) for doc in result.scalars().all()]


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
async def upload_document(
	file: UploadFile = File(...),
	db: AsyncSession = Depends(get_db),
	_: User = Depends(require_roles(UserRole.admin)),
) -> DocumentPublic:
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

	document = DocumentMetadata(
		source_type=DocumentSourceType.loi,
		titre=file.filename or local_path.name,
		langue="fr",
		statut=DocumentStatus.en_vigueur,
		categorie_infraction=["non_classe"],
		storage_path=str(local_path),
		original_filename=file.filename or local_path.name,
		size_bytes=len(content),
		ingestion_status=IngestionStatus.processing,
	)
	db.add(document)
	await db.commit()
	await db.refresh(document)

	# Synchronous extraction/chunking/indexing: acceptable for an admin-only, low-volume
	# upload flow given there is no background job queue in this codebase yet.
	try:
		text = _extract_text(local_path, suffix)
		chunks = chunk_document(document.original_filename, text)
		if not chunks:
			raise ValueError("No extractable text found in document")

		document.langue = chunks[0].langue
		for chunk in chunks:
			index_chunk_in_qdrant(
				f"{document.id}::{chunk.chunk_index}",
				document,
				chunk.text,
				numero_article=chunk.numero_article,
			)

		document.ingestion_status = IngestionStatus.indexed
		document.chunk_count = len(chunks)
		document.ingestion_error = None
	except Exception as exc:
		document.ingestion_status = IngestionStatus.failed
		document.ingestion_error = str(exc)[:2000]

	await db.commit()
	await db.refresh(document)
	return _to_document_public(document)
