import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE_NAME = "fiscalmind_session";
const PROTECTED_PREFIXES = ["/chat", "/history", "/admin", "/profile"];
const AUTH_PAGES = ["/login", "/register"];

export function middleware(request: NextRequest) {
	const hasSession = !!request.cookies.get(COOKIE_NAME)?.value;
	const { pathname } = request.nextUrl;

	const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
	const isAuthPage = AUTH_PAGES.includes(pathname);

	if (isProtected && !hasSession) {
		const url = request.nextUrl.clone();
		url.pathname = "/login";
		return NextResponse.redirect(url);
	}

	// Deja connecte : l'accueil public et les pages de connexion menent a l'application.
	if ((isAuthPage || pathname === "/") && hasSession) {
		const url = request.nextUrl.clone();
		url.pathname = "/chat";
		return NextResponse.redirect(url);
	}

	return NextResponse.next();
}

export const config = {
	matcher: ["/", "/chat/:path*", "/history/:path*", "/admin/:path*", "/profile/:path*", "/login", "/register"],
};
