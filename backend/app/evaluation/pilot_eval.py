"""Etape 6 du pilote : comparaison des variantes A/B/C/D.

A = pilote_base            C = pilote_ctx
B = pilote_base + statut   D = pilote_ctx + statut
"+ statut" = reponderation des sources par statut d'edition ET sources annotees
(annee, statut) dans le prompt de generation, avec consigne de privilegier le
texte en vigueur.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.app.enrichment.pilot_index import BASE, CTX, PilotHit

VARIANTS = {
	"A_base": (BASE, False),
	"B_base_statut": (BASE, True),
	"C_ctx": (CTX, False),
	"D_ctx_statut": (CTX, True),
}

STATUT_LABEL = {"en_vigueur": "edition en vigueur", "remplacee": "edition REMPLACEE", "texte_date": "texte date", "indetermine": "statut inconnu"}

SYSTEM_PROMPT = (
	"Tu es un assistant juridique specialise en fiscalite tunisienne. Reponds UNIQUEMENT a partir des "
	"sources fournies. N'invente rien. Si les sources ne permettent pas de repondre, dis-le explicitement."
)
STATUT_INSTRUCTION = (
	"Chaque source indique son annee et son statut. Si plusieurs sources donnent des regles differentes, "
	"applique celle de l'edition EN VIGUEUR la plus recente et precise l'edition ou la loi citee."
)

JUDGE_V2_PROMPT = """Tu es un evaluateur expert en fiscalite tunisienne.
On te donne une QUESTION, la REPONSE DE REFERENCE (regle actuellement en vigueur), les FAITS CLES attendus,
des ERREURS TYPIQUES (regles perimees ou mal appliquees) et la REPONSE d'un assistant.

Bareme : 5 = correcte et complete ; 4 = correcte, detail mineur manquant ; 3 = partiellement correcte ;
2 = majoritairement incorrecte ; 1 = fausse, perimee ou refus alors que la reponse existe.

QUESTION : {question}
REPONSE DE REFERENCE : {reference}
FAITS CLES : {faits_cles}
ERREURS TYPIQUES : {faits_errones}
REPONSE DE L'ASSISTANT : {answer}

Reponds UNIQUEMENT avec ce JSON :
{{"score": <1-5>, "verdict": "correct"|"partiel"|"incorrect", "regle_perimee": true|false, "justification": "<une ou deux phrases>"}}"""


def format_sources(hits: list[PilotHit], with_statut: bool) -> str:
	blocks = []
	for i, h in enumerate(hits, start=1):
		head = f"[Source {i}] {h.source_file}"
		if with_statut:
			head += f" ({h.annee or 'annee inconnue'}, {STATUT_LABEL.get(h.statut_version or '', 'statut inconnu')})"
		blocks.append(f"{head}\n{h.texte}")
	return "\n\n".join(blocks) if blocks else "Aucune source trouvee."


def generation_prompt(question: str, hits: list[PilotHit], with_statut: bool) -> str:
	parts = [f"Question : {question}", "", "Sources disponibles :", format_sources(hits, with_statut), ""]
	if with_statut:
		parts.append(STATUT_INSTRUCTION)
	parts.append("Reponds a la question en te basant uniquement sur ces sources.")
	return "\n".join(parts)


# --- metriques de recherche -------------------------------------------------

def recall_at_k(retrieved: list[str], expected: list[str], k: int = 5) -> float:
	if not expected:
		return 0.0
	return len(set(retrieved[:k]) & set(expected)) / len(set(expected))


def ndcg_at_k(retrieved: list[str], expected: list[str], k: int = 5) -> float:
	rel = set(expected)
	dcg = sum(1 / math.log2(i + 2) for i, c in enumerate(retrieved[:k]) if c in rel)
	ideal = sum(1 / math.log2(i + 2) for i in range(min(len(rel), k)))
	return dcg / ideal if ideal else 0.0


def reciprocal_rank(retrieved: list[str], expected: list[str]) -> float:
	for i, c in enumerate(retrieved, start=1):
		if c in set(expected):
			return 1 / i
	return 0.0


@dataclass
class VigueurMetrics:
	correct_in_top5: bool  # une source de la regle en vigueur (attendu ou equivalent) est dans le top 5
	correct_before_trap: bool  # la premiere source correcte arrive avant le premier piege
	trap_at_1: bool  # le 1er resultat est un piege (ancienne regle)
	trap_share_top5: float  # part des pieges dans le top 5


def vigueur_metrics(retrieved: list[str], correct: list[str], traps: list[str], k: int = 5) -> VigueurMetrics:
	top = retrieved[:k]
	correct_ranks = [i for i, c in enumerate(top) if c in set(correct)]
	trap_ranks = [i for i, c in enumerate(top) if c in set(traps)]
	first_correct = correct_ranks[0] if correct_ranks else None
	first_trap = trap_ranks[0] if trap_ranks else None
	return VigueurMetrics(
		correct_in_top5=first_correct is not None,
		correct_before_trap=first_correct is not None and (first_trap is None or first_correct < first_trap),
		trap_at_1=bool(top) and top[0] in set(traps),
		trap_share_top5=len(trap_ranks) / len(top) if top else 0.0,
	)


def mean(values: list[float]) -> float | None:
	values = [v for v in values if v is not None]
	return sum(values) / len(values) if values else None
