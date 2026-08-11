export type HealthResponse = {
	status: string;
	service: string;
	version?: string;
};

export type QueryRequest = {
	question: string;
	language?: "fr" | "ar";
};

export type Citation = {
	article_id: string;
	loi: string;
	numero_article: number;
	statut: string;
	langue: string;
	extrait: string;
};

export type QueryResponse = {
	query_id: string;
	final_answer: string;
	verification_status: string;
	citations: Citation[];
	disclaimer: string;
};

const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
	const response = await fetch(`${API_BASE_URL}/health`, {
		method: "GET",
		cache: "no-store",
	});

	if (!response.ok) {
		throw new Error(`Health check failed with status ${response.status}`);
	}

	return (await response.json()) as HealthResponse;
}

export async function postQuery(
	payload: QueryRequest,
	accessToken?: string,
): Promise<QueryResponse> {
	const response = await fetch(`${API_BASE_URL}/api/v1/query`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
		},
		body: JSON.stringify(payload),
	});

	if (!response.ok) {
		throw new Error(`Query failed with status ${response.status}`);
	}

	return (await response.json()) as QueryResponse;
}
