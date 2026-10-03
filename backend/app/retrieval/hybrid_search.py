from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
	article_id: str
	loi: str
	numero_article: int
	statut: str
	langue: str
	extrait: str
	category: str
	dense_score: float = 0.0
	sparse_score: float = 0.0
	fused_score: float = 0.0


@dataclass
class JurisprudenceChunk:
	case_id: str
	reference: str
	resume: str
	langue: str
	categorie: str
	dense_score: float = 0.0
	sparse_score: float = 0.0
	fused_score: float = 0.0


def tokenize(text: str) -> set[str]:
	return {part.strip(".,;:!?()[]{}\"'\n\t").lower() for part in text.split() if part.strip()}


def deterministic_embedding(text: str, vector_size: int) -> list[float]:
	if vector_size <= 0:
		return []

	v = [0.0 for _ in range(vector_size)]
	tokens = tokenize(text)
	if not tokens:
		return v

	for token in tokens:
		idx = abs(hash(token)) % vector_size
		v[idx] += 1.0

	norm = sum(x * x for x in v) ** 0.5
	if norm == 0:
		return v
	return [x / norm for x in v]
