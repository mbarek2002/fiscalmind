from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.ingestion.indexing_by_article import search_by_article_hybrid
from backend.app.llm.factory import get_llm_client

DEFAULT_TOP_K = 5

SYSTEM_PROMPT = (
	"Tu es un assistant juridique specialise en fiscalite tunisienne. "
	"Reponds a la question UNIQUEMENT a partir des sources fournies ci-dessous. "
	"N'invente rien. Si les sources ne permettent pas de repondre, dis-le explicitement."
)


@dataclass
class SimpleAgentResult:
	question: str
	answer: str
	# Textes bruts des chunks recuperes (pas juste leurs ids) -- RAGAS a besoin du
	# texte du contexte, pas d'un identifiant, pour juger Faithfulness/Relevancy.
	contexts: list[str]
	# chunk_id des sources, dans le meme ordre que contexts (rapport d'evaluation).
	source_ids: list[str] = field(default_factory=list)


def answer_question(question: str, language: str = "fr", top_k: int = DEFAULT_TOP_K) -> SimpleAgentResult:
	"""Agent simple : retrieve puis generate, sans qualify/rerank/verify -- le
	niveau de simplicite du pipeline retrieve-then-generate observe dans le repo
	compare, sert de base a l'evaluation RAGAS (Faithfulness, Answer Relevancy).
	Pipeline LangGraph existant (graph.py, graph_by_article.py) non touche."""
	results = search_by_article_hybrid(question=question, language=language, top_k=top_k)
	contexts = [r.texte for r in results]

	context_block = "\n\n".join(f"- {c}" for c in contexts) if contexts else "Aucune source trouvee."
	user_prompt = (
		f"Question : {question}\n\n"
		f"Sources disponibles :\n{context_block}\n\n"
		"Reponds a la question en te basant uniquement sur ces sources."
	)

	answer = get_llm_client().generate(prompt=user_prompt, system_prompt=SYSTEM_PROMPT)

	return SimpleAgentResult(
		question=question,
		answer=answer or "",
		contexts=contexts,
		source_ids=[r.id_chunk for r in results],
	)
