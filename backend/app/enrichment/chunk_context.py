"""Passe 2 : enrichissement d'un chunk a partir de la fiche de son document et
de ses voisins (contextual retrieval).

Garde-fous :
- articles_contenus : gardes seulement si "Article N" figure dans le chunk ;
- taux_seuils : gardes seulement si la preuve est dans le chunk ET contient la valeur ;
- contexte : un chiffre absent du chunk et de la fiche le rend suspect -> remplace
  par un contexte construit par regle (aucune invention possible) ;
- impots / infractions / role : listes fermees.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from backend.app.enrichment.document_fiche import IMPOTS, normalize

INFRACTIONS = [
	"retard_paiement", "defaut_declaration", "retenue_source", "paiement_especes", "timbre",
	"prix_transfert", "taxation_office", "facturation", "regime_forfaitaire", "autre",
]
ROLES = ["client", "fournisseur", "contribuable", "employeur", "administration", "tous"]

CHUNK_PROMPT = """Tu enrichis un extrait d'un document fiscal tunisien pour un moteur de recherche juridique.

FICHE DU DOCUMENT :
{fiche}

FIN DE L'EXTRAIT PRECEDENT :
{avant}

EXTRAIT A ENRICHIR :
<<<
{texte}
>>>

DEBUT DE L'EXTRAIT SUIVANT :
{apres}

REGLES STRICTES :
- Ne decris QUE l'extrait a enrichir ; n'invente aucun chiffre, taux, montant ou article.
- "contexte" : 1 a 2 phrases qui situent l'extrait (document, edition/annee, partie ou chapitre,
  sujet traite). Aucun chiffre qui ne figure pas dans l'extrait ou dans la fiche.
- "articles_contenus" : numeros d'articles dont le TEXTE figure dans l'extrait (ex. "81", "80 sexies"),
  pas les articles seulement cites en reference.
- "taux_seuils" : les 8 taux, montants ou seuils les plus importants de l'extrait (8 maximum),
  chacun avec une "preuve" courte (5 a 15 mots) copiee mot pour mot.
- "impots" parmi {impots} ; "infractions" parmi {infractions} ; "role" parmi {roles} ou null.

Reponds UNIQUEMENT avec ce JSON :
{{"contexte": str, "section": str|null, "articles_contenus": [str], "themes": [str, 4 maximum],
  "impots": [str], "infractions": [str], "role": str|null,
  "taux_seuils": [{{"valeur": str, "description": str, "preuve": str}}]}}"""


@dataclass
class ChunkEnrichment:
	chunk_id: str
	source_file: str
	contexte: str
	contexte_source: str  # llm | regle
	section: str | None
	articles_contenus: list[str]
	themes: list[str]
	impots: list[str]
	infractions: list[str]
	role: str | None
	taux_seuils: list[dict]
	annee: int | None
	statut_version: str
	type_document: str
	famille: str
	rejets: list[str] = field(default_factory=list)
	llm_ok: bool = True

	def to_dict(self) -> dict:
		return asdict(self)


def compact_fiche(fiche: dict) -> str:
	keys = ["titre", "reference", "famille", "type_document", "annee", "statut_version", "remplacee_par", "loi_commentee", "resume"]
	data = {k: fiche.get(k) for k in keys if fiche.get(k)}
	data["plan"] = (fiche.get("plan") or [])[:15]
	return json.dumps(data, ensure_ascii=False)


def rule_context(fiche: dict) -> str:
	"""Contexte sans LLM, a partir de la seule fiche."""
	label = fiche.get("titre") or fiche.get("reference") or fiche.get("fichier")
	parts = [str(label)]
	if fiche.get("annee"):
		parts.append(f"edition/annee {fiche['annee']}")
	statut = {"en_vigueur": "edition en vigueur", "remplacee": "edition remplacee", "texte_date": "texte date"}.get(fiche.get("statut_version"))
	if statut:
		parts.append(statut)
	return " - ".join(parts) + "."


def _numbers(text: str) -> set[str]:
	return {re.sub(r"[ .]", "", n).replace(",", ".") for n in re.findall(r"\d+(?:[ .,]\d+)*", text or "")}


def article_in_text(article: str, chunk_text: str) -> bool:
	num, _, suffix = article.strip().partition(" ")
	if not num.isdigit():
		return False
	pattern = r"art(?:icle)?\.?\s*" + re.escape(num) + r"\b" + (r"\s*" + re.escape(suffix) if suffix else "")
	return re.search(pattern, normalize(chunk_text)) is not None


def validate_enrichment(raw: dict, chunk_text: str, fiche: dict) -> tuple[dict, list[str]]:
	rejects: list[str] = []
	chunk_norm = normalize(chunk_text)
	out: dict = {}

	contexte = (raw.get("contexte") or "").strip()
	allowed = _numbers(chunk_text) | _numbers(compact_fiche(fiche))
	invented = sorted(n for n in _numbers(contexte) if n not in allowed)
	if not contexte or invented:
		if invented:
			rejects.append(f"contexte: chiffres absents du chunk et de la fiche {invented}")
		out["contexte"], out["contexte_source"] = rule_context(fiche), "regle"
	else:
		out["contexte"], out["contexte_source"] = contexte, "llm"

	articles = []
	for a in raw.get("articles_contenus") or []:
		a = re.sub(r"\s+", " ", str(a).lower().replace("article", "").strip())
		if article_in_text(a, chunk_text):
			articles.append(a)
		else:
			rejects.append(f"article {a!r} absent du chunk")
	out["articles_contenus"] = list(dict.fromkeys(articles))

	taux = []
	for t in (raw.get("taux_seuils") or [])[:8]:
		valeur, preuve = str(t.get("valeur") or ""), str(t.get("preuve") or "")
		if preuve and normalize(preuve) in chunk_norm and _numbers(valeur) and _numbers(valeur) <= _numbers(preuve):
			taux.append({"valeur": valeur, "description": str(t.get("description") or ""), "preuve": preuve})
		else:
			rejects.append(f"taux {valeur!r} sans preuve valide")
	out["taux_seuils"] = taux

	out["section"] = raw.get("section") or None
	out["themes"] = [str(x) for x in (raw.get("themes") or [])][:4]
	out["impots"] = [i for i in (raw.get("impots") or []) if i in IMPOTS]
	out["infractions"] = [i for i in (raw.get("infractions") or []) if i in INFRACTIONS]
	out["role"] = raw.get("role") if raw.get("role") in ROLES else None
	return out, rejects


def build_prompt(fiche: dict, chunk_text: str, before: str, after: str) -> str:
	return CHUNK_PROMPT.format(
		fiche=compact_fiche(fiche),
		avant=(before or "(debut du document)")[-600:],
		texte=chunk_text,
		apres=(after or "(fin du document)")[:600],
		impots=", ".join(IMPOTS),
		infractions=", ".join(INFRACTIONS),
		roles=", ".join(ROLES),
	)


def enrich_chunk(chunk_id: str, chunk_text: str, fiche: dict, raw: dict | None) -> ChunkEnrichment:
	base = {
		"chunk_id": chunk_id,
		"source_file": fiche["fichier"],
		"annee": fiche.get("annee"),
		"statut_version": fiche.get("statut_version", "indetermine"),
		"type_document": fiche.get("type_document", "autre"),
		"famille": fiche.get("famille", "AUTRE"),
	}
	if not raw:
		return ChunkEnrichment(
			**base, contexte=rule_context(fiche), contexte_source="regle", section=None, articles_contenus=[],
			themes=[], impots=[], infractions=[], role=None, taux_seuils=[], rejets=["llm en echec"], llm_ok=False,
		)
	values, rejects = validate_enrichment(raw, chunk_text, fiche)
	return ChunkEnrichment(**base, **values, rejets=rejects)
