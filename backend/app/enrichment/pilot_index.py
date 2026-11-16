"""Collections Qdrant du pilote et recherche parametrable.

- pilote_base : memes chunks, memes vecteurs que la production (copie), texte
  BM25 = texte d'origine ; metadonnees de document/chunk ajoutees au payload.
- pilote_ctx  : texte indexe = contexte LLM + texte d'origine (vecteur E5
  recalcule et BM25 sur ce texte) ; memes metadonnees.

La seule difference entre les deux est donc le texte indexe : on mesure l'effet
du contexte. La ponderation par statut d'edition (prefer_en_vigueur) se teste
sur les deux, pour mesurer l'effet des metadonnees separement.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from backend.app.core.config import get_settings
from backend.app.ingestion.embedding_e5 import embed_passages, embed_query
from backend.app.ingestion.indexing_by_article import point_id_for_chunk

BASE = "pilote_base"
CTX = "pilote_ctx"
TEXT_FIELD = {BASE: "texte", CTX: "texte_indexe"}

# Poids appliques au score de fusion : une edition remplacee recule nettement,
# un texte date (note commune) un peu, l'edition en vigueur reste intacte.
STATUT_WEIGHTS = {"en_vigueur": 1.0, "indetermine": 0.9, "texte_date": 0.85, "remplacee": 0.5}

META_KEYS = [
	"annee", "statut_version", "type_document", "famille", "contexte", "contexte_source", "section",
	"articles_contenus", "themes", "impots", "infractions", "role", "taux_seuils",
]


def client() -> QdrantClient:
	s = get_settings()
	return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key)


def recreate_collection(name: str) -> None:
	c = client()
	if c.collection_exists(name):
		c.delete_collection(name)
	c.create_collection(
		collection_name=name,
		vectors_config={"dense": models.VectorParams(size=get_settings().e5_embedding_dim, distance=models.Distance.COSINE)},
	)
	c.create_payload_index(
		collection_name=name,
		field_name=TEXT_FIELD[name],
		field_schema=models.TextIndexParams(
			type=models.TextIndexType.TEXT, scoring=models.TextScoringParams(type=models.TextScoringType.BM25)
		),
	)
	for field, schema in [("langue", models.PayloadSchemaType.KEYWORD), ("statut_version", models.PayloadSchemaType.KEYWORD), ("annee", models.PayloadSchemaType.INTEGER)]:
		c.create_payload_index(collection_name=name, field_name=field, field_schema=schema)


def indexed_text(enrichment: dict, texte: str) -> str:
	"""Texte indexe de pilote_ctx : le contexte situe le passage avant son contenu."""
	parts = [enrichment.get("contexte") or ""]
	if enrichment.get("section"):
		parts.append(str(enrichment["section"]))
	parts.append(texte)
	return "\n".join(p for p in parts if p)


def build_collections(source_files: list[str], enrichments: dict[str, dict], batch: int = 64) -> dict[str, int]:
	"""Construit les deux collections a partir de la collection de production."""
	settings = get_settings()
	c = client()
	recreate_collection(BASE)
	recreate_collection(CTX)
	flt = models.Filter(must=[models.FieldCondition(key="source_file", match=models.MatchAny(any=source_files))])

	counts = {BASE: 0, CTX: 0}
	offset = None
	while True:
		points, offset = c.scroll(
			collection_name=settings.qdrant_collection_loi_by_article,
			scroll_filter=flt, limit=batch, offset=offset, with_payload=True, with_vectors=True,
		)
		if points:
			base_points, ctx_payloads = [], []
			for p in points:
				enr = enrichments.get(p.payload["id_chunk"], {})
				meta = {k: enr.get(k) for k in META_KEYS}
				base_points.append(models.PointStruct(id=p.id, vector={"dense": p.vector["dense"]}, payload={**p.payload, **meta}))
				ctx_payloads.append({**p.payload, **meta, "texte_indexe": indexed_text(enr, p.payload["texte"])})
			ctx_vectors = embed_passages([pl["texte_indexe"] for pl in ctx_payloads])
			ctx_points = [
				models.PointStruct(id=point_id_for_chunk(pl["id_chunk"]), vector={"dense": v}, payload=pl)
				for pl, v in zip(ctx_payloads, ctx_vectors)
			]
			c.upsert(collection_name=BASE, points=base_points)
			c.upsert(collection_name=CTX, points=ctx_points)
			counts[BASE] += len(base_points)
			counts[CTX] += len(ctx_points)
		if offset is None:
			return counts


@dataclass
class PilotHit:
	id_chunk: str
	source_file: str
	texte: str
	score: float
	statut_version: str | None
	annee: int | None
	payload: dict


def apply_statut_weights(hits: list[PilotHit]) -> list[PilotHit]:
	"""Reordonne les candidats : score x poids du statut d'edition."""
	for h in hits:
		h.score = h.score * STATUT_WEIGHTS.get(h.statut_version or "indetermine", 0.9)
	return sorted(hits, key=lambda h: h.score, reverse=True)


def search(collection: str, question: str, top_k: int = 5, prefer_en_vigueur: bool = False, language: str = "fr") -> list[PilotHit]:
	"""Hybride E5 + BM25 (RRF), comme la production ; avec prefer_en_vigueur, on
	recupere plus de candidats puis on les repondere par statut d'edition."""
	c = client()
	vector = embed_query(question)
	flt = models.Filter(must=[models.FieldCondition(key="langue", match=models.MatchValue(value=language))])
	pool = top_k * (4 if prefer_en_vigueur else 1)
	candidate_limit = max(pool * 3, pool)
	response = c.query_points(
		collection_name=collection,
		prefetch=[
			models.Prefetch(query=vector, using="dense", filter=flt, limit=candidate_limit),
			models.Prefetch(query=models.TextQuery(text=question), using=TEXT_FIELD[collection], filter=flt, limit=candidate_limit),
		],
		query=models.FusionQuery(fusion=models.Fusion.RRF),
		limit=pool,
		with_payload=True,
	)
	hits = [
		PilotHit(
			id_chunk=p.payload["id_chunk"], source_file=p.payload.get("source_file", ""), texte=p.payload.get("texte", ""),
			score=float(p.score), statut_version=p.payload.get("statut_version"), annee=p.payload.get("annee"), payload=p.payload,
		)
		for p in response.points
	]
	if prefer_en_vigueur:
		hits = apply_statut_weights(hits)
	return hits[:top_k]
