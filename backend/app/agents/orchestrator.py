from backend.app.agents.legal_retrieval import collect_graph_context_ids, retrieve_legal_candidates
from backend.app.agents.qualification import qualify_question
from backend.app.agents.reranker import rerank_legal_results
from backend.app.agents.state import AgentState
from backend.app.agents.synthesis import synthesize_answer
from backend.app.agents.verifier import verify_citations


def run_query_pipeline(question: str, language: str) -> AgentState:
	lang = "ar" if language == "ar" else "fr"
	legal_candidates = retrieve_legal_candidates(question=question, language=lang, top_k=3)
	legal_results = rerank_legal_results(question=question, legal_candidates=legal_candidates, top_k=3)
	graph_context_ids = collect_graph_context_ids(legal_results)
	category = qualify_question(question, legal_results)
	final_answer, citations = synthesize_answer(
		question=question,
		category=category,
		language=lang,
		legal_results=legal_results,
		graph_context_ids=graph_context_ids,
	)
	verification = verify_citations(
		citations=citations,
		legal_results=legal_results,
		expected_language=lang,
	)

	if verification.status == "rejected":
		final_answer = (
			"La reponse automatique n'a pas pu etre verifiee de maniere fiable. "
			"Merci de reformuler la question ou de consulter un professionnel du droit."
		)

	return {
		"user_query": question,
		"language": lang,
		"category": category,
		"legal_result_ids": [row.article_id for row in legal_results],
		"graph_context_ids": graph_context_ids,
		"final_answer": final_answer,
		"verification_status": verification.status,
		"verification_notes": verification.notes,
		"citations": verification.verified_citations,
	}
