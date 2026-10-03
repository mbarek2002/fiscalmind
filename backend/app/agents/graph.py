from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from backend.app.agents.legal_retrieval import collect_graph_context_ids, retrieve_legal_candidates
from backend.app.agents.qualification import qualify_question
from backend.app.agents.reranker import rerank_legal_results
from backend.app.agents.state import AgentState
from backend.app.agents.synthesis import synthesize_answer
from backend.app.agents.verifier import verify_citations


def _build_submission_text(structured_data: dict | None, free_text: str | None) -> str:
	"""Turn a FinancialSubmission's structured_data + free_text into one text blob, reusing
	the same qualification/retrieval/synthesis logic built for free-text questions rather than
	writing a separate threshold-comparison path (deferred — see QUESTIONS_SITUATION_FINANCIERE.md)."""
	parts: list[str] = []
	if structured_data:
		parts.extend(f"{key}: {value}" for key, value in structured_data.items())
	if free_text:
		parts.append(free_text)
	return ". ".join(parts)


def analyze_financial_situation(state: AgentState) -> AgentState:
	"""Single node: qualify -> retrieve -> rerank -> synthesize -> verify, in one pass (no
	retry loop yet — that becomes a conditional edge once this node is split into several)."""
	language = state.get("language", "fr")
	question_text = _build_submission_text(state.get("structured_data"), state.get("free_text"))

	top_k = 3
	legal_candidates = retrieve_legal_candidates(question=question_text, language=language, top_k=top_k)
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


def build_financial_analysis_graph():
	"""Compiled LangGraph: one node today. Adding agents later means adding nodes/edges here —
	not rewriting this into a different framework."""
	graph = StateGraph(AgentState)
	graph.add_node("analyze_financial_situation", analyze_financial_situation)
	graph.add_edge(START, "analyze_financial_situation")
	graph.add_edge("analyze_financial_situation", END)
	return graph.compile()


@lru_cache
def get_financial_analysis_graph():
	"""Compile once per process and reuse — compiling is cheap but there's no reason to repeat
	it on every request, consistent with how get_embedding_client()/the reranker are cached."""
	return build_financial_analysis_graph()
