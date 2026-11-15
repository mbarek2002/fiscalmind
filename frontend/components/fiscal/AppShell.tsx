"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
	Landmark,
	MessageSquare,
	History,
	UserCircle2,
	FileStack,
	Activity,
	LogOut,
	Menu,
	X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { authStore } from "@/lib/auth";
import type { User } from "@/lib/types";
import { RoleBadge } from "./RoleBadge";
import { cn } from "@/lib/utils";

const NAV = [
	{ to: "/chat", label: "Consultation", Icon: MessageSquare },
	{ to: "/history", label: "Historique", Icon: History },
	{ to: "/admin/documents", label: "Documents", Icon: FileStack },
	{ to: "/health", label: "Santé système", Icon: Activity },
	{ to: "/profile", label: "Profil", Icon: UserCircle2 },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [open, setOpen] = useState(false);
	const router = useRouter();
	const pathname = usePathname();

	useEffect(() => {
		setUser(authStore.getUser());
	}, []);

	useEffect(() => {
		setOpen(false);
	}, [pathname]);

	const handleLogout = () => {
		authStore.clear();
		router.push("/login");
	};

	return (
		// Coque fixe a la hauteur de l'ecran : seule la zone <main> (et, dans le chat,
		// la conversation et les citations) defile -- jamais la page entiere.
		<div className="flex h-dvh w-full overflow-hidden">
			{/* Sidebar */}
			<aside
				className={cn(
					"fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-sidebar text-sidebar-foreground transition-transform lg:static lg:translate-x-0",
					open ? "translate-x-0" : "-translate-x-full",
				)}
				aria-label="Navigation principale"
			>
				<div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-5">
					<Landmark className="h-6 w-6 text-white" aria-hidden />
					<div>
						<p className="font-display text-base font-bold leading-none text-white">FiscalMind</p>
						<p className="mt-0.5 text-[11px] text-white/60">Loi de finance · Tunisie</p>
					</div>
				</div>
				<nav className="flex-1 space-y-1 px-3 py-4">
					{NAV.map(({ to, label, Icon }) => {
						const active = pathname === to || pathname.startsWith(to + "/");
						return (
							<Link
								key={to}
								href={to}
								className={cn(
									"flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
									active
										? "bg-sidebar-accent text-white"
										: "text-white/75 hover:bg-sidebar-accent/60 hover:text-white",
								)}
							>
								<Icon className="h-4 w-4" aria-hidden />
								{label}
							</Link>
						);
					})}
				</nav>
				<div className="border-t border-sidebar-border p-3">
					<Button
						onClick={handleLogout}
						variant="ghost"
						className="w-full justify-start text-white/80 hover:bg-sidebar-accent hover:text-white"
					>
						<LogOut className="mr-2 h-4 w-4" /> Se déconnecter
					</Button>
				</div>
			</aside>

			{open && (
				<button
					type="button"
					aria-label="Fermer le menu"
					onClick={() => setOpen(false)}
					className="fixed inset-0 z-30 bg-black/40 lg:hidden"
				/>
			)}

			{/* Main */}
			<div className="flex min-h-0 min-w-0 flex-1 flex-col">
				<header className="z-20 flex h-16 shrink-0 items-center gap-3 border-b border-border-soft bg-card/80 px-4 backdrop-blur lg:px-8">
					<Button
						variant="ghost"
						size="icon"
						className="lg:hidden"
						onClick={() => setOpen((v) => !v)}
						aria-label={open ? "Fermer la navigation" : "Ouvrir la navigation"}
					>
						{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
					</Button>
					<h1 className="hidden font-display text-lg font-semibold sm:block">
						{NAV.find((n) => pathname === n.to || pathname.startsWith(n.to + "/"))?.label ??
							"FiscalMind"}
					</h1>
					<div className="ml-auto flex items-center gap-3">
						{user && (
							<>
								<div className="hidden text-right sm:block">
									<p className="text-sm font-medium leading-tight">{user.full_name}</p>
									<p className="text-xs text-text-muted">{user.email}</p>
								</div>
								<RoleBadge role={user.role} />
							</>
						)}
					</div>
				</header>
				<main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 lg:px-8 lg:py-6">{children}</main>
			</div>
		</div>
	);
}
