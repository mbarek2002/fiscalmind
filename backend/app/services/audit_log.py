from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.db_models import AuditLog, QueryCitation, QueryLog, User


async def persist_query_and_audit(
	db: AsyncSession,
	user: User,
	query_id: str,
	question: str,
	final_answer: str,
	verification_status: str,
	citations: list[dict],
) -> None:
	query_log = QueryLog(
		id=query_id,
		user_id=user.id,
		question=question,
		final_answer=final_answer,
		verification_status=verification_status,
	)
	db.add(query_log)

	for item in citations:
		db.add(
			QueryCitation(
				query_log_id=query_id,
				article_id=item["article_id"],
				loi=item["loi"],
				numero_article=item["numero_article"],
				statut=item["statut"],
				langue=item["langue"],
				extrait=item["extrait"],
			)
		)

	db.add(
		AuditLog(
			user_id=user.id,
			user_role=user.role.value,
			query_id=query_id,
			question=question,
			final_answer=final_answer,
			citations=citations,
			verification_status=verification_status,
			retry_count=0,
		)
	)
	await db.commit()
