export type UserRole = "citoyen" | "avocat" | "juge" | "admin";
export type Language = "fr" | "ar";

export interface User {
	id: string;
	email: string;
	full_name: string;
	role: UserRole;
	language: Language;
}

export interface AuthResponse {
	access_token: string;
	refresh_token?: string;
	user: User;
}

export interface Citation {
	article_id: string;
	loi: string;
	numero_article: number;
	statut: "en_vigueur" | "abroge" | "modifie" | "en_cours" | string;
	langue: Language;
	extrait: string;
}

export type VerificationStatus = "verifie" | "partiel" | "non_verifie" | "incertain" | string;

export interface QueryRequest {
	question: string;
	language: Language;
}

export interface QueryResponse {
	query_id: string;
	final_answer: string;
	verification_status: VerificationStatus;
	citations: Citation[];
	disclaimer: string;
	created_at?: string;
	question?: string;
}

export interface HealthResponse {
	status: "ok" | "degraded" | "down" | string;
	service?: string;
	version?: string;
	uptime_seconds?: number;
	services?: Record<string, "ok" | "down" | string>;
}

export interface AdminDocument {
	id: string;
	filename: string;
	size_bytes: number;
	uploaded_at: string;
	status: "uploaded" | "processing" | "indexed" | "failed";
	chunks?: number;
	error?: string | null;
}
