"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "@/lib/api";
import { authStore } from "@/lib/auth";
import { AppShell } from "@/components/fiscal/AppShell";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
	const router = useRouter();
	const [ready, setReady] = useState(false);

	useEffect(() => {
		let cancelled = false;

		async function checkSession() {
			if (!authStore.isAuthenticated()) {
				router.replace("/login");
				return;
			}
			try {
				const user = await api.me();
				if (cancelled) return;
				authStore.setUser(user);
				setReady(true);
			} catch (err) {
				if (cancelled) return;
				if (err instanceof ApiError && err.status === 401) {
					authStore.clear();
					router.replace("/login");
				} else {
					// Backend unreachable for a reason other than auth: keep the cached
					// session usable instead of forcing a logout on a transient error.
					setReady(true);
				}
			}
		}

		checkSession();
		return () => {
			cancelled = true;
		};
	}, [router]);

	if (!ready) {
		return (
			<div className="flex min-h-dvh items-center justify-center text-sm text-text-muted">
				Chargement…
			</div>
		);
	}

	return <AppShell>{children}</AppShell>;
}
