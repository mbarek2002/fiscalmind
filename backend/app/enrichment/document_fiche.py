"""Passe 1 : fiche d'un document par LLM (document entier), fusionnee avec les
regles.

Garde-fous :
- sortie JSON validee ;
- les champs factuels (titre, reference, annee, loi commentee) doivent etre
  accompagnes d'une citation exacte retrouvee dans le texte, sinon rejetes ;
- en cas de desaccord sur l'annee, les regles gagnent et le conflit est note.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from dataclasses import asdict, dataclass, field

from backend.app.core.config import Settings, get_settings
from backend.app.enrichment.document_rules import RuleFacts, code_famille_from_title
from backend.app.enrichment.versions import VersionStatus

IMPOTS = [
	"IRPP", "IS", "TVA", "retenue_source", "droits_enregistrement", "timbre",
	"fiscalite_locale", "procedures_sanctions", "droits_consommation", "conventions_fiscales", "autre",
]

FICHE_PROMPT = """Tu analyses un document juridique fiscal tunisien. Lis-le en entier et produis sa fiche.

REGLES STRICTES :
- N'invente rien. Si une information n'est pas dans le texte, mets null.
- Pour titre, reference, annee et loi_commentee, donne dans "preuve" une citation EXACTE
  (copiee mot pour mot, 3 a 25 mots) du texte qui justifie la valeur.
- "annee" : annee de l'edition (code), de la loi (loi de finances), de la note (note commune)
  ou de la signature (convention).
- "impots_concernes" : choisis uniquement dans {impots}.

Reponds UNIQUEMENT avec ce JSON :
{{
  "titre": {{"valeur": str|null, "preuve": str|null}},
  "type_document": "code"|"loi_finances"|"loi_finances_complementaire"|"note_commune"|"convention"|"decret"|"recueil"|"autre",
  "reference": {{"valeur": str|null, "preuve": str|null}},
  "annee": {{"valeur": int|null, "preuve": str|null}},
  "loi_commentee": {{"valeur": str|null, "preuve": str|null}},
  "pays": str|null,
  "impots_concernes": [str],
  "themes": [str, ... 6 maximum],
  "plan": [str, ... 15 titres principaux maximum],
  "resume": "3 phrases maximum"
}}

<document>
{texte}
</document>"""

PROOF_FIELDS = ("titre", "reference", "annee", "loi_commentee")


def normalize(text: str) -> str:
	"""Comparaison tolerante : casse, accents, apostrophes et espaces ignores
	(le LLM recopie souvent "fevrier" pour "février")."""
	text = unicodedata.normalize("NFKD", (text or "").replace("’", "'"))
	text = "".join(c for c in text if not unicodedata.combining(c))
	return re.sub(r"\s+", " ", text).strip().lower()


def parse_json_object(raw: str) -> dict:
	match = re.search(r"\{.*\}", raw or "", re.DOTALL)
	if not match:
		raise ValueError(f"pas de JSON dans la reponse : {raw[:200]!r}")
	return json.loads(match.group(0))


@dataclass
class DocumentFiche:
	fichier: str
	famille: str
	type_document: str
	annee: int | None
	annee_source: str | None
	reference: str | None
	titre: str | None
	loi_commentee: str | None
	pays: str | None
	impots_concernes: list[str]
	themes: list[str]
	plan: list[str]
	resume: str | None
	statut_version: str
	remplacee_par: str | None
	nb_chunks: int
	preuves: dict[str, str] = field(default_factory=dict)
	rejets: list[str] = field(default_factory=list)
	conflits: list[str] = field(default_factory=list)
	llm_ok: bool = True

	def to_dict(self) -> dict:
		return asdict(self)


def validate_llm_fields(raw: dict, document_text: str) -> tuple[dict, dict[str, str], list[str]]:
	"""Garde un champ factuel seulement si sa preuve figure dans le document
	(et, pour l'annee, si l'annee figure dans la preuve)."""
	doc = normalize(document_text)
	values: dict = {}
	proofs: dict[str, str] = {}
	rejects: list[str] = []
	for name in PROOF_FIELDS:
		item = raw.get(name) or {}
		value, proof = item.get("valeur"), item.get("preuve")
		if value in (None, ""):
			continue
		if not proof or normalize(proof) not in doc:
			rejects.append(f"{name}: preuve introuvable dans le texte ({proof!r})")
			continue
		if name == "annee":
			try:
				value = int(value)
			except (TypeError, ValueError):
				rejects.append(f"annee: valeur non entiere ({value!r})")
				continue
			if str(value) not in proof:
				rejects.append(f"annee: {value} absente de la preuve ({proof!r})")
				continue
		values[name] = value
		proofs[name] = proof
	return values, proofs, rejects


def merge_fiche(
	fichier: str,
	rules: RuleFacts,
	version: VersionStatus,
	llm_raw: dict | None,
	document_text: str,
	nb_chunks: int,
) -> DocumentFiche:
	llm_raw = llm_raw or {}
	values, proofs, rejects = validate_llm_fields(llm_raw, document_text) if llm_raw else ({}, {}, [])
	conflicts: list[str] = []

	annee, annee_source = rules.annee, rules.annee_source
	if rules.annee_preuve:
		proofs["annee_regle"] = rules.annee_preuve
	if values.get("annee") is not None:
		if annee is None:
			annee, annee_source = values["annee"], "llm"
		elif values["annee"] != annee:
			conflicts.append(f"annee : regles={annee} ({rules.annee_source}) / llm={values['annee']}")

	famille = rules.famille
	type_document = rules.type_document
	llm_type = llm_raw.get("type_document")
	# Fichier au nom muet (ex. "11.pdf") mais dont le titre revele un code : on le
	# rattache a sa famille. Son edition est inconnue : l'annee trouvee en 1re page
	# est celle d'une loi citee, pas de l'edition -> on ne la garde pas.
	code_famille = code_famille_from_title(values.get("titre")) if famille == "AUTRE" else None
	if code_famille:
		conflicts.append(f"famille : AUTRE -> {code_famille} d'apres le titre ; edition inconnue (annee {annee} ignoree)")
		famille, type_document, annee, annee_source = code_famille, "code", None, None
	elif type_document == "autre" and llm_type:
		type_document = llm_type
	elif llm_type and llm_type != type_document:
		conflicts.append(f"type : regles={type_document} / llm={llm_type}")

	impots = [i for i in (llm_raw.get("impots_concernes") or []) if i in IMPOTS]

	return DocumentFiche(
		fichier=fichier,
		famille=famille,
		type_document=type_document,
		annee=annee,
		annee_source=annee_source,
		reference=rules.reference or values.get("reference"),
		titre=values.get("titre"),
		loi_commentee=values.get("loi_commentee"),
		pays=llm_raw.get("pays"),
		impots_concernes=impots,
		themes=list(llm_raw.get("themes") or [])[:6],
		plan=list(llm_raw.get("plan") or [])[:15],
		resume=llm_raw.get("resume"),
		statut_version=version.statut_version,
		remplacee_par=version.remplacee_par,
		nb_chunks=nb_chunks,
		preuves=proofs,
		rejets=rejects,
		conflits=conflicts,
		llm_ok=bool(llm_raw),
	)


class FicheLLM:
	"""Appel NVIDIA (format OpenAI), temperature 0, sans mode reflexion."""

	def __init__(self, settings: Settings | None = None, model: str | None = None, max_retries: int = 4) -> None:
		from openai import OpenAI

		settings = settings or get_settings()
		if not settings.nvidia_api_key:
			raise RuntimeError("NVIDIA_API_KEY est requis pour l'enrichissement")
		self._client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key, timeout=300)
		self.model = model or settings.nvidia_llm_model
		self._max_retries = max_retries

	def ask_json(self, prompt: str, max_tokens: int = 2500) -> dict:
		last: Exception | None = None
		for attempt in range(self._max_retries):
			try:
				response = self._client.chat.completions.create(
					model=self.model,
					messages=[{"role": "user", "content": prompt}],
					temperature=0.0,
					max_tokens=max_tokens,
					extra_body={"chat_template_kwargs": {"enable_thinking": False}},
				)
				return parse_json_object(response.choices[0].message.content or "")
			except Exception as exc:
				last = exc
				time.sleep(3 * (attempt + 1))
		raise RuntimeError(f"echec LLM apres {self._max_retries} essais : {last!r}")

	def fiche(self, fichier: str, document_text: str) -> dict:
		# Le nom de fichier n'est pas transmis : sinon le LLM le cite comme "preuve".
		prompt = FICHE_PROMPT.format(impots=", ".join(IMPOTS), texte=document_text)
		return self.ask_json(prompt)
