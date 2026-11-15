"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, Calendar, ArrowLeft } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { VerificationStatusPill } from "@/components/fiscal/VerificationStatusPill";
import { CitationCard } from "@/components/fiscal/CitationCard";
import { LegalDisclaimer } from "@/components/fiscal/LegalDisclaimer";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/fiscal/states";
import type { QueryResponse } from "@/lib/types";

function formatDate(iso?: string) {
	if (!iso) return "";
	return new Date(iso).toLocaleString("fr-FR", {
		dateStyle: "medium",
		timeStyle: "short",
	});
}

export default function HistoryPage() {
	const [history, setHistory] = useState<QueryResponse[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [q, setQ] = useState("");
	const [from, setFrom] = useState("");
	const [to, setTo] = useState("");
	const [selected, setSelected] = useState<QueryResponse | null>(null);

	const load = async () => {
		setLoading(true);
		setError(null);
		try {
			setHistory(await api.getHistory());
		} catch (err) {
			setError(err instanceof ApiError ? err.message : "Impossible de charger l'historique");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		load();
	}, []);

	const filtered = useMemo(() => {
		return history.filter((item) => {
			const matchQ =
				!q ||
				(item.question ?? "").toLowerCase().includes(q.toLowerCase()) ||
				item.final_answer.toLowerCase().includes(q.toLowerCase());
			const created = item.created_at ? new Date(item.created_at).getTime() : 0;
			const matchFrom = !from || created >= new Date(from).getTime();
			const matchTo = !to || created <= new Date(to).getTime() + 86_400_000;
			return matchQ && matchFrom && matchTo;
		});
	}, [history, q, from, to]);

	if (loading) {
		return (
			<div className="mx-auto max-w-4xl">
				<LoadingSkeleton lines={5} />
			</div>
		);
	}

	if (error) {
		return (
			<div className="mx-auto max-w-4xl">
				<ErrorState title="Historique indisponible" description={error} onRetry={load} />
			</div>
		);
	}

	if (selected) {
		return (
			<div className="mx-auto max-w-4xl space-y-4">
				<Button variant="ghost" size="sm" onClick={() => setSelected(null)}>
					<ArrowLeft className="mr-1.5 h-4 w-4" /> Retour à l&apos;historique
				</Button>
				<div className="surface-card p-6">
					<div className="flex flex-wrap items-center justify-between gap-2">
						<p className="text-xs text-text-muted">{formatDate(selected.created_at)}</p>
						<VerificationStatusPill status={selected.verification_status} />
					</div>
					<h2 className="mt-2 font-display text-xl font-bold">{selected.question}</h2>
					<p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-text-strong">
						{selected.final_answer}
					</p>
				</div>
				<div>
					<h3 className="mb-2 font-display text-sm font-bold uppercase tracking-wide text-text-muted">
						Citations ({selected.citations.length})
					</h3>
					<div className="grid gap-3 md:grid-cols-2">
						{selected.citations.map((c) => (
							<CitationCard key={c.article_id} citation={c} />
						))}
					</div>
				</div>
				<LegalDisclaimer />
			</div>
		);
	}

	return (
		<div className="mx-auto max-w-4xl space-y-6">
			<div className="surface-card p-4 lg:p-6">
				<div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
					<div>
						<Label htmlFor="search-history" className="sr-only">
							Rechercher
						</Label>
						<div className="relative">
							<Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-faint" />
							<Input
								id="search-history"
								value={q}
								onChange={(e) => setQ(e.target.value)}
								placeholder="Rechercher dans mes requêtes…"
								className="pl-9"
							/>
						</div>
					</div>
					<div>
						<Label htmlFor="from" className="text-xs text-text-muted">
							<Calendar className="mr-1 inline h-3 w-3" /> Du
						</Label>
						<Input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
					</div>
					<div>
						<Label htmlFor="to" className="text-xs text-text-muted">
							Au
						</Label>
						<Input id="to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
					</div>
				</div>
			</div>

			{filtered.length === 0 ? (
				<EmptyState
					title="Aucune requête trouvée"
					description="Ajustez vos filtres ou lancez une nouvelle consultation."
				/>
			) : (
				<ul className="space-y-3">
					{filtered.map((item) => (
						<li key={item.query_id}>
							<button
								onClick={() => setSelected(item)}
								className="surface-card w-full p-4 text-left transition hover:border-primary-500 hover:shadow-md"
							>
								<div className="flex flex-wrap items-center justify-between gap-2">
									<p className="text-xs text-text-muted">{formatDate(item.created_at)}</p>
									<VerificationStatusPill status={item.verification_status} />
								</div>
								<h3 className="mt-1 font-display text-base font-semibold text-text-strong">
									{item.question}
								</h3>
								<p className="mt-1 line-clamp-2 text-sm text-text-muted">{item.final_answer}</p>
								<p className="mt-2 text-xs font-semibold text-primary-700">
									{item.citations.length} citation{item.citations.length > 1 ? "s" : ""} →
								</p>
							</button>
						</li>
					))}
				</ul>
			)}
		</div>
	);
}
