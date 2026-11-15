import type { AuthResponse, User } from "./types";

const TOKEN_KEY = "fiscalmind.token";
const REFRESH_KEY = "fiscalmind.refresh_token";
const USER_KEY = "fiscalmind.user";
export const CHAT_KEY_PREFIX = "fiscalmind.chat.";
// Mirrors the access token into a plain (non-httpOnly) cookie so middleware.ts can
// gate routes at the edge. Readable by JS like localStorage — same XSS exposure,
// not a security upgrade, just what's possible without a backend-issued cookie.
const COOKIE_NAME = "fiscalmind_session";
const COOKIE_MAX_AGE_DAYS = 7;

function setCookie(value: string) {
	if (typeof document === "undefined") return;
	document.cookie = `${COOKIE_NAME}=${value}; path=/; max-age=${COOKIE_MAX_AGE_DAYS * 24 * 60 * 60}; samesite=lax`;
}

function clearCookie() {
	if (typeof document === "undefined") return;
	document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; samesite=lax`;
}

export const authStore = {
	getToken(): string | null {
		if (typeof window === "undefined") return null;
		return window.localStorage.getItem(TOKEN_KEY);
	},
	setToken(token: string) {
		if (typeof window === "undefined") return;
		window.localStorage.setItem(TOKEN_KEY, token);
		setCookie(token);
	},
	getRefreshToken(): string | null {
		if (typeof window === "undefined") return null;
		return window.localStorage.getItem(REFRESH_KEY);
	},
	setRefreshToken(token: string) {
		if (typeof window === "undefined") return;
		window.localStorage.setItem(REFRESH_KEY, token);
	},
	getUser(): User | null {
		if (typeof window === "undefined") return null;
		const raw = window.localStorage.getItem(USER_KEY);
		if (!raw) return null;
		try {
			return JSON.parse(raw) as User;
		} catch {
			return null;
		}
	},
	setUser(user: User) {
		if (typeof window === "undefined") return;
		window.localStorage.setItem(USER_KEY, JSON.stringify(user));
	},
	setSession(auth: AuthResponse) {
		authStore.setToken(auth.access_token);
		if (auth.refresh_token) authStore.setRefreshToken(auth.refresh_token);
		authStore.setUser(auth.user);
	},
	clear() {
		if (typeof window === "undefined") return;
		window.localStorage.removeItem(TOKEN_KEY);
		window.localStorage.removeItem(REFRESH_KEY);
		window.localStorage.removeItem(USER_KEY);
		clearCookie();
		// Conversations en cours (chat/page.tsx) : ne pas les laisser au compte suivant.
		try {
			Object.keys(window.sessionStorage)
				.filter((key) => key.startsWith(CHAT_KEY_PREFIX))
				.forEach((key) => window.sessionStorage.removeItem(key));
		} catch {
			// stockage indisponible (navigation privee...) : rien a nettoyer
		}
	},
	isAuthenticated(): boolean {
		return !!authStore.getToken();
	},
};
