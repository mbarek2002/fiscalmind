from __future__ import annotations


def normalize_vector_size(vector: list[float], expected_size: int) -> list[float]:
	if expected_size <= 0:
		return vector
	if len(vector) == expected_size:
		return vector
	if len(vector) > expected_size:
		return vector[:expected_size]
	return vector + [0.0] * (expected_size - len(vector))
