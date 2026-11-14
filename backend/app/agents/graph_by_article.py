from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from backend.app.agents.legal_retrieval import collect_graph_context_ids
from backend.app.agents.legal_retrieval_by_article import retrieve_legal_candidates_by_article
from backend.app.agents.qualification import qualify_question
from backend.app.agents.reranker import rerank_legal_results
from backend.app.agents.state import AgentState
from backend.app.agents.synthesis import synthesize_answer
from backend.app.agents.verifier import verify_citations


def _build_submission_text(structured_data: dict | None, free_text: str | None) -> str:
	parts: list[str] = []
	if structured_data:
		parts.extend(f"{key}: {value}" for key, value in structured_data.items())
	if free_text:
		parts.append(free_text)
	return ". ".join(parts)


def analyze_financial_situation_by_article(state: AgentState) -> AgentState:
	"""Variante de analyze_financial_situation (graph.py, inchange) : seule l'etape
	de retrieve change (nouveau pipeline E5 + chunking par article + BM25 natif au
	lieu de BGE-M3 + chunking par taille). Rerank, qualify, synthesize et verify
	sont les memes fonctions, reutilisees sans modification -- elles ne dependent
	que du type RetrievedChunk, pas de la maniere dont il a ete produit."""
	language = state.get("language", "fr")
	question_text = _build_submission_text(state.get("structured_data"), state.get("free_text"))

	top_k = 3
	legal_candidates = retrieve_legal_candidates_by_article(question=question_text, language=language, top_k=top_k)
	legal_results = rerank_legal_results(question=question_text, legal_candidates=legal_candidates, top_k=top_k)
	graph_context_ids = collect_graph_context_ids(legal_results)
	category = qualify_question(question_text, legal_results)

	final_answer, citations = synthesize_answer(
		question=question_text,
		category=category,
		language=language,
		legal_results=legal_results,
		graph_context_ids=graph_context_ids,
	)
	verification = verify_citations(citations=citations, legal_results=legal_results, expected_language=language)

	return {
		**state,
		"user_query": question_text,
		"category": category,
		"legal_result_ids": [row.article_id for row in legal_results],
		"graph_context_ids": graph_context_ids,
		"final_answer": final_answer,
		"verification_status": verification.status,
		"verification_notes": verification.notes,
		"citations": verification.verified_citations,
	}


def build_financial_analysis_graph_by_article():
	graph = StateGraph(AgentState)
	graph.add_node("analyze_financial_situation_by_article", analyze_financial_situation_by_article)
	graph.add_edge(START, "analyze_financial_situation_by_article")
	graph.add_edge("analyze_financial_situation_by_article", END)
	return graph.compile()


@lru_cache
def get_financial_analysis_graph_by_article():
	return build_financial_analysis_graph_by_article()
