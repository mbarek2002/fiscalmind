from backend.app.agents.prompts.synthesis_prompt import load_synthesis_prompt_templates, render_prompt
from backend.app.agents.state import Citation
from backend.app.core.config import get_settings
from backend.app.llm.factory import get_llm_client
from backend.app.retrieval.hybrid_search import RetrievedChunk


def synthesize_answer(
	question: str,
	category: str,
	language: str,
	legal_results: list[RetrievedChunk],
	graph_context_ids: list[str],
) -> tuple[str, list[Citation]]:
	citations: list[Citation] = [
		{
			"article_id": row.article_id,
			"loi": row.loi,
			"numero_article": row.numero_article,
			"statut": row.statut,
			"langue": row.langue,
			"extrait": row.extrait,
		}
		for row in legal_results
	]

	context_lines = [
		f"- {row.loi} / article {row.numero_article} [{row.langue}] ({row.statut}) : {row.extrait}"
		for row in legal_results
	]
	context_block = "\n".join(context_lines) if context_lines else "Aucun article recupere."

	system_template, user_template = load_synthesis_prompt_templates()
	system_prompt = system_template
	user_prompt = render_prompt(
		user_template,
		language=language,
		category=category,
		question=question,
		graph_context_ids=", ".join(graph_context_ids) if graph_context_ids else "aucun",
		context_block=context_block,
	)

	try:
		answer = get_llm_client().generate(prompt=user_prompt, system_prompt=system_prompt)
		if not answer:
			raise ValueError("Empty LLM answer")
	except Exception as exc:
		if get_settings().provider_strict_mode_enabled:
			raise RuntimeError(
				"LLM provider is unavailable or returned an invalid response while strict provider mode is enabled"
			) from exc
		answer = (
			"Reponse RAG v0 (fallback). "
			f"Categorie estimee: {category}. "
			f"Articles analyses: {len(legal_results)}. "
			f"Relations graphe: {len(graph_context_ids)}. "
			f"Question recue: {question}"
		)

	return answer, citations
