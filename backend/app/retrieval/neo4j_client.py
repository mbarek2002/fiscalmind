from __future__ import annotations

from backend.app.core.config import get_settings


def fetch_related_articles(article_id: str) -> list[str]:
	settings = get_settings()
	if not settings.neo4j_uri or not settings.neo4j_username or not settings.neo4j_password:
		return []

	try:
		from neo4j import GraphDatabase
	except Exception:
		return []

	query = """
	MATCH (a:Article {id: $article_id})
	OPTIONAL MATCH (a)-[:MODIFIE|ABROGE]-(rel:Article)
	RETURN collect(DISTINCT rel.id) AS related_ids
	"""

	try:
		driver = GraphDatabase.driver(
			settings.neo4j_uri,
			auth=(settings.neo4j_username, settings.neo4j_password),
		)
		with driver.session() as session:
			result = session.run(query, article_id=article_id).single()
			related = result["related_ids"] if result and "related_ids" in result else []
			return [item for item in related if item]
	except Exception:
		return []
	finally:
		try:
			driver.close()  # type: ignore[name-defined]
		except Exception:
			pass
