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

	system_prompt = (
		"Tu es un assistant juridique specialise en loi de finance tunisienne. "
		"N'invente jamais une source. Cite uniquement les extraits fournis. "
		"Si les informations sont insuffisantes, dis-le explicitement."
	)
	user_prompt = (
		f"Langue de reponse: {language}\n"
		f"Categorie estimee: {category}\n"
		f"Question utilisateur: {question}\n"
		f"IDs de contexte graphe: {', '.join(graph_context_ids) if graph_context_ids else 'aucun'}\n\n"
		"Sources disponibles:\n"
		f"{context_block}\n\n"
		"Donne une reponse claire, concise, et strictement basee sur ces sources."
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
