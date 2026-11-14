"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, CheckCircle2, XCircle, RefreshCcw, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";
import { LoadingSkeleton, ErrorState } from "@/components/fiscal/states";
import { cn } from "@/lib/utils";

export default function HealthPage() {
	const [data, setData] = useState<HealthResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const load = async () => {
		setLoading(true);
		setError(null);
		try {
			const res = await api.health();
			setData(res);
		} catch (err) {
			setError(err instanceof ApiError ? err.message : "Impossible de joindre le backend");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		load();
	}, []);

	const isUp = data?.status === "ok";

	return (
		<div className="mx-auto max-w-3xl px-4 py-10 lg:px-8">
			<Link href="/" className="mb-4 inline-flex items-center gap-2 text-sm text-text-muted hover:text-primary-700">
				<ArrowLeft className="h-4 w-4" /> Retour à l&apos;accueil
			</Link>
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div>
					<h1 className="font-display text-3xl font-bold">Santé système</h1>
					<p className="mt-1 text-sm text-text-muted">
						Ping du backend FiscalMind et détail par service.
					</p>
				</div>
				<Button onClick={load} variant="outline" size="sm" disabled={loading}>
					<RefreshCcw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} /> Rafraîchir
				</Button>
			</div>

			<div className="mt-6 space-y-4">
				{loading && <LoadingSkeleton lines={5} />}
				{error && !loading && (
					<ErrorState title="Backend injoignable" description={error} onRetry={load} />
				)}
				{!loading && !error && data && (
					<>
						<div
							className={cn(
								"surface-card flex items-center gap-4 p-6",
								isUp ? "border-success/30" : "border-danger/30",
							)}
						>
							<div
								className={cn(
									"flex h-12 w-12 items-center justify-center rounded-full",
									isUp ? "bg-success-badge text-success" : "bg-error-badge text-danger",
								)}
							>
								{isUp ? <CheckCircle2 className="h-6 w-6" /> : <XCircle className="h-6 w-6" />}
							</div>
							<div>
								<p className="font-display text-lg font-semibold">
									Statut : {isUp ? "Opérationnel" : String(data.status).toUpperCase()}
								</p>
								<p className="text-sm text-text-muted">
									Version {data.version ?? "n/a"} · Uptime {(data.uptime_seconds ?? 0) | 0} s
								</p>
							</div>
							<Activity className="ml-auto h-6 w-6 text-primary-500" aria-hidden />
						</div>

						{data.services && (
							<div className="surface-card p-6">
								<h2 className="font-display text-sm font-bold uppercase tracking-wide text-text-muted">
									Services
								</h2>
								<ul className="mt-3 divide-y divide-border-soft">
									{Object.entries(data.services).map(([name, status]) => {
										const ok = status === "ok";
										return (
											<li key={name} className="flex items-center justify-between py-2.5">
												<span className="text-sm font-medium capitalize">
													{name.replace(/_/g, " ")}
												</span>
												<span
													className={cn(
														"inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
														ok
															? "bg-success-badge text-success"
															: "bg-error-badge text-danger",
													)}
												>
													{ok ? (
														<CheckCircle2 className="h-3.5 w-3.5" />
													) : (
														<XCircle className="h-3.5 w-3.5" />
													)}
													{ok ? "OK" : String(status)}
												</span>
											</li>
										);
									})}
								</ul>
							</div>
						)}
					</>
				)}
			</div>
		</div>
	);
}
