from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.orchestrator import run_query_pipeline
from backend.app.api.deps import get_current_user, get_db
from backend.app.models.db_models import User
from backend.app.models.schemas import QueryRequest, QueryResponse
from backend.app.services.audit_log import persist_query_and_audit


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def run_query(
	payload: QueryRequest,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> QueryResponse:
	state = run_query_pipeline(
		question=payload.question,
		language=payload.language,
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
	)

	return QueryResponse(
		query_id=query_id,
		final_answer=state["final_answer"],
		verification_status=state["verification_status"],
		citations=state["citations"],
		disclaimer="Cette reponse ne constitue pas un avis juridique officiel.",
	)
