import { authStore } from "./auth";
import { LEGAL_DISCLAIMER, mockDocuments, mockHistory, mockQueryResponse } from "./mock";
import type {
	AdminDocument,
	AuthResponse,
	HealthResponse,
	Language,
	QueryRequest,
	QueryResponse,
	User,
	UserRole,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const NO_RETRY_PATHS = new Set(["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/register"]);

export class ApiError extends Error {
	status: number;
	details?: unknown;
	constructor(message: string, status: number, details?: unknown) {
		super(message);
		this.status = status;
		this.details = details;
	}
}

interface BackendUser {
	id: string;
	email: string;
	full_name: string;
	role: UserRole;
	preferred_lang: "fr" | "ar";
}

interface BackendTokenPair {
	access_token: string;
	refresh_token: string;
	user: BackendUser;
}

function mapUser(raw: BackendUser): User {
	return {
		id: raw.id,
		email: raw.email,
		full_name: raw.full_name,
		role: raw.role,
		language: raw.preferred_lang,
	};
}

function mapAuthResponse(raw: BackendTokenPair): AuthResponse {
	return {
		access_token: raw.access_token,
		refresh_token: raw.refresh_token,
		user: mapUser(raw.user),
	};
}

// Le backend fait tourner les refresh tokens : chacun n'est utilisable qu'UNE fois.
// Plusieurs requetes en 401 simultanees (React StrictMode lance les effets deux fois,
// plusieurs onglets...) ne doivent donc partager qu'un seul appel /auth/refresh,
// sinon le second est refuse ("already revoked") et l'utilisateur est deconnecte.
let refreshInFlight: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
	const refreshToken = authStore.getRefreshToken();
	if (!refreshToken) return false;
	try {
		const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ refresh_token: refreshToken }),
		});
		if (res.ok) {
			const raw = (await res.json()) as BackendTokenPair;
			authStore.setSession(mapAuthResponse(raw));
			return true;
		}
		// Un autre onglet a peut-etre deja fait la rotation : si le token stocke a
		// change entre-temps, la session est toujours valide.
		return authStore.getRefreshToken() !== refreshToken;
	} catch {
		return false;
	}
}

function refreshAccessToken(): Promise<boolean> {
	if (!refreshInFlight) {
		refreshInFlight = doRefresh().finally(() => {
			refreshInFlight = null;
		});
	}
	return refreshInFlight;
}

async function request<T>(path: string, init: RequestInit = {}, allowRefresh = true): Promise<T> {
	const headers = new Headers(init.headers);
	headers.set("Content-Type", "application/json");
	const token = authStore.getToken();
	if (token) headers.set("Authorization", `Bearer ${token}`);

	const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

	if (res.status === 401 && allowRefresh && !NO_RETRY_PATHS.has(path)) {
		const refreshed = await refreshAccessToken();
		if (refreshed) return request<T>(path, init, false);
		authStore.clear();
	}

	const contentType = res.headers.get("content-type") ?? "";
	const body = contentType.includes("application/json") ? await res.json().catch(() => null) : await res.text();

	if (!res.ok) {
		const message =
			(body && typeof body === "object" && "detail" in body && String((body as { detail: unknown }).detail)) ||
			(body && typeof body === "object" && "message" in body && String((body as { message: unknown }).message)) ||
			`Erreur ${res.status}`;
		throw new ApiError(message, res.status, body);
	}
	return body as T;
}

const USE_MOCK = !BASE_URL;

function delay(ms: number) {
	return new Promise((r) => setTimeout(r, ms));
}

export const api = {
	usesMock: USE_MOCK,

	async health(): Promise<HealthResponse> {
		if (USE_MOCK) {
			await delay(400);
			return {
				status: "ok",
				version: "0.1.0-dev",
				uptime_seconds: 3421,
				services: { database: "ok", vector_store: "ok", llm_gateway: "ok" },
			};
		}
		return request<HealthResponse>("/health");
	},

	async login(email: string, password: string): Promise<AuthResponse> {
		if (USE_MOCK) {
			await delay(500);
			const role: UserRole = email.includes("juge")
				? "juge"
				: email.includes("avocat")
					? "avocat"
					: "citoyen";
			const user: User = {
				id: "usr-" + email,
				email,
				full_name: email.split("@")[0].replace(".", " "),
				role,
				language: "fr",
			};
			return { access_token: "mock-token-" + Date.now(), user };
		}
		const raw = await request<BackendTokenPair>("/api/v1/auth/login", {
			method: "POST",
			body: JSON.stringify({ email, password }),
		});
		return mapAuthResponse(raw);
	},

	async register(input: {
		email: string;
		password: string;
		full_name: string;
	}): Promise<AuthResponse> {
		if (USE_MOCK) {
			await delay(600);
			const user: User = {
				id: "usr-" + input.email,
				email: input.email,
				full_name: input.full_name,
				role: "citoyen",
				language: "fr",
			};
			return { access_token: "mock-token-" + Date.now(), user };
		}
		// The backend's /auth/register only returns the created profile (no tokens) —
		// log in right after to obtain a real token pair for the new account.
		await request<BackendUser>("/api/v1/auth/register", {
			method: "POST",
			body: JSON.stringify(input),
		});
		return api.login(input.email, input.password);
	},

	async me(): Promise<User> {
		if (USE_MOCK) {
			const u = authStore.getUser();
			if (!u) throw new ApiError("Non authentifié", 401);
			return u;
		}
		const raw = await request<BackendUser>("/api/v1/auth/me");
		return mapUser(raw);
	},

	async query(input: QueryRequest): Promise<QueryResponse> {
		if (USE_MOCK) {
			await delay(1200);
			return { ...mockQueryResponse(input.question), disclaimer: LEGAL_DISCLAIMER };
		}
		return request<QueryResponse>("/api/v1/query", {
			method: "POST",
			body: JSON.stringify(input),
		});
	},

	async getHistory(): Promise<QueryResponse[]> {
		if (USE_MOCK) {
			await delay(300);
			return mockHistory;
		}
		return request<QueryResponse[]>("/api/v1/query/history");
	},

	async getDocuments(): Promise<AdminDocument[]> {
		if (USE_MOCK) {
			await delay(300);
			return mockDocuments;
		}
		return request<AdminDocument[]>("/api/v1/documents");
	},

	async uploadDocument(file: File): Promise<AdminDocument> {
		if (USE_MOCK) {
			await delay(500);
			return {
				id: crypto.randomUUID(),
				filename: file.name,
				size_bytes: file.size,
				uploaded_at: new Date().toISOString(),
				status: "indexed",
				chunks: Math.max(1, Math.round(file.size / 2000)),
			};
		}
		const token = authStore.getToken();
		const formData = new FormData();
		formData.append("file", file);
		const res = await fetch(`${BASE_URL}/api/v1/documents`, {
			method: "POST",
			headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			body: formData,
		});
		const body = await res.json().catch(() => null);
		if (!res.ok) {
			const message =
				(body && typeof body === "object" && "detail" in body && String((body as { detail: unknown }).detail)) ||
				`Erreur ${res.status}`;
			throw new ApiError(message, res.status, body);
		}
		return body as AdminDocument;
	},

	async updateProfile(input: { preferred_lang?: Language; full_name?: string }): Promise<User> {
		if (USE_MOCK) {
			await delay(300);
			const current = authStore.getUser();
			if (!current) throw new ApiError("Non authentifié", 401);
			const updated: User = {
				...current,
				...(input.full_name ? { full_name: input.full_name } : {}),
				...(input.preferred_lang ? { language: input.preferred_lang } : {}),
			};
			authStore.setUser(updated);
			return updated;
		}
		const raw = await request<BackendUser>("/api/v1/users/me", {
			method: "PATCH",
			body: JSON.stringify(input),
		});
		return mapUser(raw);
	},
};
