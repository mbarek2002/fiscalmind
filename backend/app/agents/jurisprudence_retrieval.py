def retrieve_jurisprudence(question: str, top_k: int = 2) -> list[dict]:
	entries = [
		{
			"case_id": "jp_2021_014",
			"reference": "Affaire 2021-014",
			"resume": "Cas de non declaration partielle de TVA avec regularisation tardive.",
		},
		{
			"case_id": "jp_2022_031",
			"reference": "Affaire 2022-031",
			"resume": "Contentieux fiscal avec contestation de base imposable.",
		},
	]
	return entries[:top_k]
