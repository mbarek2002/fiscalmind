from datetime import date
from typing import Literal, NotRequired, TypedDict


class Citation(TypedDict):
	article_id: str
	loi: str
	numero_article: int
	statut: str
	langue: str
	extrait: str


class JurisprudenceCitation(TypedDict):
	case_id: str
	reference: str
	resume: str


class AgentState(TypedDict):
	user_query: str
	language: Literal["fr", "ar"]
	user_role: str
	date_des_faits: date
	category: str
	legal_result_ids: list[str]
	jurisprudence_result_ids: list[str]
	graph_context_ids: list[str]
	final_answer: str
	verification_status: str
	verification_notes: str
	retry_count: int
	citations: list[Citation]
	jurisprudence: list[JurisprudenceCitation]

	# FinancialSubmission context (société -> situation financière), used by the
	# financial-analysis graph instead of a free-text user_query. NotRequired: the existing
	# question-answering pipeline (run_query_pipeline) never sets these.
	submission_id: NotRequired[str]
	company_id: NotRequired[str]
	source_type: NotRequired[str]
	structured_data: NotRequired[dict | None]
	free_text: NotRequired[str | None]
