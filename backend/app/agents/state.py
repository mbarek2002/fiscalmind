from typing import Literal, TypedDict


class Citation(TypedDict):
	article_id: str
	loi: str
	numero_article: int
	statut: str
	langue: str
	extrait: str


class AgentState(TypedDict):
	user_query: str
	language: Literal["fr", "ar"]
	category: str
	legal_result_ids: list[str]
	graph_context_ids: list[str]
	final_answer: str
	verification_status: str
	verification_notes: str
	citations: list[Citation]
