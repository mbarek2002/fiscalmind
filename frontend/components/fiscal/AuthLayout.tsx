import Link from "next/link";
import type { ReactNode } from "react";
import { Landmark } from "lucide-react";
import { Label } from "@/components/ui/label";
import { LegalDisclaimer } from "./LegalDisclaimer";

export function AuthLayout({
	title,
	subtitle,
	children,
	footer,
}: {
	title: string;
	subtitle: string;
	children: ReactNode;
	footer: ReactNode;
}) {
	return (
		<div className="grid min-h-dvh lg:grid-cols-2">
			<div className="hidden flex-col justify-between bg-primary-900 p-10 text-white lg:flex">
				<Link href="/" className="flex items-center gap-2">
					<span className="flex h-9 w-9 items-center justify-center rounded-md bg-white/10">
						<Landmark className="h-5 w-5" />
					</span>
					<div>
						<p className="font-display text-lg font-bold">FiscalMind</p>
						<p className="text-xs text-white/60">Loi de finance · Tunisie</p>
					</div>
				</Link>
				<div>
					<h2 className="font-display text-3xl font-bold leading-tight">
						L&apos;expertise fiscale tunisienne, à portée de question.
					</h2>
					<p className="mt-3 max-w-md text-white/70">
						Un assistant institutionnel avec citations vérifiées, pensé pour la rigueur juridique.
					</p>
				</div>
				<p className="text-xs text-white/50">
					© {new Date().getFullYear()} FiscalMind — Tous droits réservés.
				</p>
			</div>
			<div className="flex items-center justify-center px-4 py-10 lg:px-10">
				<div className="w-full max-w-md">
					<Link
						href="/"
						className="mb-6 inline-flex items-center gap-2 text-sm text-text-muted hover:text-primary-700 lg:hidden"
					>
						<Landmark className="h-4 w-4" /> FiscalMind
					</Link>
					<h1 className="font-display text-2xl font-bold">{title}</h1>
					<p className="mt-1 text-sm text-text-muted">{subtitle}</p>
					<div className="surface-card mt-6 p-6">{children}</div>
					<p className="mt-4 text-center text-sm text-text-muted">{footer}</p>
					<LegalDisclaimer className="mt-6" />
				</div>
			</div>
		</div>
	);
}

export function Field({
	label,
	id,
	error,
	children,
}: {
	label: string;
	id: string;
	error?: string;
	children: ReactNode;
}) {
	return (
		<div className="space-y-1.5">
			<Label htmlFor={id}>{label}</Label>
			{children}
			{error && (
				<p role="alert" className="text-xs font-medium text-danger">
					{error}
				</p>
			)}
		</div>
	);
}
