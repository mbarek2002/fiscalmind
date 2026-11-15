from backend.app.agents.formatter import format_answer
from backend.app.agents.jurisprudence_retrieval import retrieve_jurisprudence
from backend.app.agents.legal_retrieval import collect_graph_context_ids
from backend.app.agents.legal_retrieval_by_article import retrieve_legal_candidates_by_article
from backend.app.agents.qualification import extract_date_des_faits, qualify_question
from backend.app.agents.reranker import rerank_legal_results
from backend.app.agents.state import AgentState
from backend.app.agents.synthesis import synthesize_answer
from backend.app.agents.verifier import verify_citations
from backend.app.core.config import get_settings


def run_query_pipeline(question: str, language: str, user_role: str = "citoyen") -> AgentState:
	lang = "ar" if language == "ar" else "fr"
	settings = get_settings()
	date_des_faits = extract_date_des_faits(question)
	max_retries = max(settings.max_verification_retries, 0)

	top_k = 3
	retry_count = 0

	while True:
		# Collection loi_finance_by_article (chunking par article, E5 + BM25).
		# L'ancienne recherche (legal_retrieval.retrieve_legal_candidates, collection
		# loi_finance) reste disponible mais n'est plus utilisee par /query.
		legal_candidates = retrieve_legal_candidates_by_article(question=question, language=lang, top_k=top_k)
		legal_results = rerank_legal_results(question=question, legal_candidates=legal_candidates, top_k=top_k)
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

		if verification.status == "validated" or retry_count >= max_retries:
			break

		# Re-recherche : elargit la fenetre de candidats avant de retenter la synthese.
		retry_count += 1
		top_k *= 2

	jurisprudence_results = retrieve_jurisprudence(question=question, language=lang, top_k=2)
	jurisprudence_citations = [
		{"case_id": row.case_id, "reference": row.reference, "resume": row.resume}
		for row in jurisprudence_results
	]

	if verification.status == "rejected":
		formatted_answer = (
			"La reponse automatique n'a pas pu etre verifiee de maniere fiable. "
			"Merci de reformuler la question ou de consulter un professionnel du droit."
		)
	else:
		formatted_answer = format_answer(
			answer=final_answer,
			user_role=user_role,
			citations=verification.verified_citations,
			jurisprudence=jurisprudence_citations,
		)

	return {
		"user_query": question,
		"language": lang,
		"user_role": user_role,
		"date_des_faits": date_des_faits,
		"category": category,
		"legal_result_ids": [row.article_id for row in legal_results],
		"jurisprudence_result_ids": [row.case_id for row in jurisprudence_results],
		"graph_context_ids": graph_context_ids,
		"final_answer": formatted_answer,
		"verification_status": verification.status,
		"verification_notes": verification.notes,
		"retry_count": retry_count,
		"citations": verification.verified_citations,
		"jurisprudence": jurisprudence_citations,
	}
