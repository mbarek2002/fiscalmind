from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.agents.orchestrator import run_query_pipeline
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.db_models import QueryLog, User
from backend.app.models.schemas import CitationSchema, QueryRequest, QueryResponse
from backend.app.services.audit_log import persist_query_and_audit


router = APIRouter()


def _to_query_response(log: QueryLog) -> QueryResponse:
	return QueryResponse(
		query_id=log.id,
		final_answer=log.final_answer,
		verification_status=log.verification_status,
		citations=[
			CitationSchema(
				article_id=c.article_id,
				loi=c.loi,
				numero_article=c.numero_article,
				statut=c.statut,
				langue=c.langue,
				extrait=c.extrait,
			)
			for c in log.citations
		],
		disclaimer="Cette reponse ne constitue pas un avis juridique officiel.",
		question=log.question,
		created_at=log.created_at,
	)


@router.post("/query", response_model=QueryResponse)
async def run_query(
	payload: QueryRequest,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> QueryResponse:
	state = run_query_pipeline(
		question=payload.question,
		language=payload.language,
		user_role=current_user.role.value,
	)
	query_id = str(uuid4())

	await persist_query_and_audit(
		db=db,
		user=current_user,
		query_id=query_id,
		question=payload.question,
		final_answer=state["final_answer"],
		verification_status=state["verification_status"],
		citations=state["citations"],
		retry_count=state["retry_count"],
	)

	return QueryResponse(
		query_id=query_id,
		final_answer=state["final_answer"],
		verification_status=state["verification_status"],
		citations=state["citations"],
		jurisprudence=state["jurisprudence"],
		disclaimer="Cette reponse ne constitue pas un avis juridique officiel.",
		question=payload.question,
	)


@router.get("/query/history", response_model=list[QueryResponse])
async def get_query_history(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	limit: int = 50,
) -> list[QueryResponse]:
	result = await db.execute(
		select(QueryLog)
		.where(QueryLog.user_id == current_user.id)
		.order_by(QueryLog.created_at.desc())
		.limit(limit)
		.options(selectinload(QueryLog.citations))
	)
	return [_to_query_response(log) for log in result.scalars().all()]
