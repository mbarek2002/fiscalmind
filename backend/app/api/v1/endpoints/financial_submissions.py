from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.agents.graph import get_financial_analysis_graph
from backend.app.api.deps import get_db, require_roles
from backend.app.models.db_models import (
	FinancialDocument,
	FinancialSubmission,
	InfractionCitation,
	InfractionFinding,
	User,
)
from backend.app.models.enums import (
	CitationType,
	FinancialDocumentStatus,
	FinancialSourceType,
	FinancialSubmissionStatus,
	UserRole,
)
from backend.app.models.schemas import (
	FinancialDocumentPublic,
	FinancialSubmissionCreateRequest,
	FinancialSubmissionPublic,
	InfractionCitationPublic,
	InfractionFindingPublic,
)


router = APIRouter(prefix="/financial-submissions")

UPLOAD_DIR = Path("data/raw/company_uploads")
SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".txt"}


def _to_document_public(doc: FinancialDocument) -> FinancialDocumentPublic:
	return FinancialDocumentPublic(
		id=doc.id,
		filename=doc.original_filename,
		size_bytes=doc.size_bytes,
		status=doc.extraction_status,
		uploaded_at=doc.created_at,
		error=doc.extraction_error,
	)


def _to_finding_public(finding: InfractionFinding) -> InfractionFindingPublic:
	return InfractionFindingPublic(
		id=finding.id,
		categorie_infraction=finding.categorie_infraction,
		description=finding.description,
		severite=finding.severite,
		confidence_score=finding.confidence_score,
		citations=[
			InfractionCitationPublic(
				id=citation.id,
				citation_type=citation.citation_type,
				ref_id=citation.ref_id,
				loi=citation.loi,
				numero_article=citation.numero_article,
				reference=citation.reference,
				statut=citation.statut,
				langue=citation.langue,
				extrait=citation.extrait,
			)
			for citation in finding.citations
		],
		created_at=finding.created_at,
	)


def _to_submission_public(submission: FinancialSubmission) -> FinancialSubmissionPublic:
	return FinancialSubmissionPublic(
		id=submission.id,
		company_id=submission.company_id,
		source_type=submission.source_type,
		status=submission.status,
		free_text=submission.free_text,
		structured_data=submission.structured_data,
		final_summary=submission.final_summary,
		verification_status=submission.verification_status,
		disclaimer=submission.disclaimer,
		documents=[_to_document_public(doc) for doc in submission.documents],
		findings=[_to_finding_public(finding) for finding in submission.findings],
		created_at=submission.created_at,
	)


async def _get_owned_submission(submission_id: str, db: AsyncSession, current_user: User) -> FinancialSubmission:
	result = await db.execute(
		select(FinancialSubmission)
		.options(
			selectinload(FinancialSubmission.documents),
			selectinload(FinancialSubmission.findings).selectinload(InfractionFinding.citations),
		)
		.where(FinancialSubmission.id == submission_id)
	)
	submission = result.scalar_one_or_none()
	if submission is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
	if current_user.role != UserRole.admin and submission.company_id != current_user.company_id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your company's submission")
	return submission


@router.post("", response_model=FinancialSubmissionPublic, status_code=status.HTTP_201_CREATED)
async def create_submission(
	payload: FinancialSubmissionCreateRequest,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(require_roles(UserRole.entreprise)),
) -> FinancialSubmissionPublic:
	if current_user.company_id is None:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account not linked to a company")

	submission = FinancialSubmission(
		company_id=current_user.company_id,
		submitted_by=current_user.id,
		source_type=payload.source_type,
		free_text=payload.free_text,
		structured_data=payload.structured_data,
		status=FinancialSubmissionStatus.pending,
	)
	db.add(submission)
	await db.commit()
	await db.refresh(submission)
	# Build the response without touching submission.documents/.findings: even assigning an
	# empty list to an unloaded relationship makes SQLAlchemy diff against the (unloaded)
	# current collection first, which lazy-loads outside of an awaited context and raises
	# MissingGreenlet under the async driver. A brand-new submission has none of either anyway.
	return FinancialSubmissionPublic(
		id=submission.id,
		company_id=submission.company_id,
		source_type=submission.source_type,
		status=submission.status,
		free_text=submission.free_text,
		structured_data=submission.structured_data,
		final_summary=submission.final_summary,
		verification_status=submission.verification_status,
		disclaimer=submission.disclaimer,
		documents=[],
		findings=[],
		created_at=submission.created_at,
	)


@router.post(
	"/{submission_id}/documents",
	response_model=FinancialDocumentPublic,
	status_code=status.HTTP_201_CREATED,
)
async def upload_submission_document(
	submission_id: str,
	file: UploadFile = File(...),
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(require_roles(UserRole.entreprise)),
) -> FinancialDocumentPublic:
	submission = await _get_owned_submission(submission_id, db, current_user)

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

	document = FinancialDocument(
		submission_id=submission.id,
		original_filename=file.filename or local_path.name,
		storage_path=str(local_path),
		mime_type=file.content_type,
		size_bytes=len(content),
		extraction_status=FinancialDocumentStatus.uploaded,
	)
	db.add(document)
	if submission.source_type in (FinancialSourceType.formulaire, FinancialSourceType.texte_libre):
		submission.source_type = FinancialSourceType.mixte
	await db.commit()
	await db.refresh(document)
	return _to_document_public(document)


@router.get("", response_model=list[FinancialSubmissionPublic])
async def list_submissions(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(require_roles(UserRole.entreprise, UserRole.admin)),
) -> list[FinancialSubmissionPublic]:
	query = (
		select(FinancialSubmission)
		.options(
			selectinload(FinancialSubmission.documents),
			selectinload(FinancialSubmission.findings).selectinload(InfractionFinding.citations),
		)
		.order_by(FinancialSubmission.created_at.desc())
	)
	if current_user.role != UserRole.admin:
		query = query.where(FinancialSubmission.company_id == current_user.company_id)
	result = await db.execute(query)
	return [_to_submission_public(submission) for submission in result.scalars().all()]


@router.get("/{submission_id}", response_model=FinancialSubmissionPublic)
async def get_submission(
	submission_id: str,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(require_roles(UserRole.entreprise, UserRole.admin)),
) -> FinancialSubmissionPublic:
	submission = await _get_owned_submission(submission_id, db, current_user)
	return _to_submission_public(submission)


@router.post("/{submission_id}/analyze", response_model=FinancialSubmissionPublic)
async def analyze_submission(
	submission_id: str,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(require_roles(UserRole.entreprise, UserRole.admin)),
) -> FinancialSubmissionPublic:
	submission = await _get_owned_submission(submission_id, db, current_user)
	if submission.status == FinancialSubmissionStatus.completed:
		return _to_submission_public(submission)

	# Captured now (already eager-loaded by _get_owned_submission) rather than read from
	# submission.documents after the commits below, which would expire the relationship and
	# lazy-load it outside an awaited context (the MissingGreenlet crash fixed earlier).
	documents_snapshot = [_to_document_public(doc) for doc in submission.documents]

	submission.status = FinancialSubmissionStatus.analyzing
	await db.commit()

	try:
		graph = get_financial_analysis_graph()
		result = graph.invoke(
			{
				"structured_data": submission.structured_data,
				"free_text": submission.free_text,
				"language": "fr",
			}
		)
	except Exception as exc:
		submission.status = FinancialSubmissionStatus.failed
		await db.commit()
		raise HTTPException(
			status_code=status.HTTP_502_BAD_GATEWAY,
			detail=f"Analysis pipeline failed: {exc}",
		) from exc

	# Single agent for now: one finding per submission, not one per detected category — that
	# split is a planned future step, not this one.
	finding = InfractionFinding(
		submission_id=submission.id,
		categorie_infraction=result.get("category") or "non_classe",
		description=result.get("final_answer") or "",
	)
	for citation in result.get("citations", []):
		finding.citations.append(
			InfractionCitation(
				citation_type=CitationType.article,
				ref_id=citation.get("article_id", ""),
				loi=citation.get("loi"),
				numero_article=citation.get("numero_article"),
				statut=citation.get("statut"),
				langue=citation.get("langue"),
				extrait=citation.get("extrait", ""),
			)
		)
	db.add(finding)

	submission.status = FinancialSubmissionStatus.completed
	submission.verification_status = result.get("verification_status")
	submission.final_summary = result.get("final_answer")
	submission.disclaimer = "Cette analyse ne constitue pas un avis juridique officiel."
	await db.commit()

	# Build the response from the Python objects already in hand (submission's own fields we
	# just set, documents_snapshot captured earlier, finding we just built) instead of
	# re-reading submission.findings — same MissingGreenlet reason as above, and a db.refresh()
	# on `finding` would equally expire `finding.citations` right before we read it.
	return FinancialSubmissionPublic(
		id=submission.id,
		company_id=submission.company_id,
		source_type=submission.source_type,
		status=submission.status,
		free_text=submission.free_text,
		structured_data=submission.structured_data,
		final_summary=submission.final_summary,
		verification_status=submission.verification_status,
		disclaimer=submission.disclaimer,
		documents=documents_snapshot,
		findings=[_to_finding_public(finding)],
		created_at=submission.created_at,
	)
