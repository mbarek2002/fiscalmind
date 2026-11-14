import { BookMarked } from "lucide-react";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUT_LABEL: Record<string, string> = {
	en_vigueur: "En vigueur",
	abroge: "Abrogé",
	modifie: "Modifié",
	en_cours: "En cours",
};

const STATUT_TONE: Record<string, string> = {
	en_vigueur: "bg-success-badge text-success",
	abroge: "bg-error-badge text-danger",
	modifie: "bg-warning-badge text-warning",
	en_cours: "bg-info-badge text-primary-700",
};

export function CitationCard({ citation, className }: { citation: Citation; className?: string }) {
	const label = STATUT_LABEL[citation.statut] ?? citation.statut;
	const tone = STATUT_TONE[citation.statut] ?? "bg-info-badge text-primary-700";
	return (
		<article
			className={cn(
				"legal-citation surface-card p-4 animate-fade-in",
				className,
			)}
			aria-label={`Citation article ${citation.numero_article}`}
		>
			<header className="flex flex-wrap items-start justify-between gap-2">
				<div className="flex items-start gap-2">
					<BookMarked className="mt-0.5 h-4 w-4 text-primary-700" aria-hidden />
					<div>
						<h4 className="text-sm font-semibold text-text-strong">Article {citation.numero_article}</h4>
						<p className="text-xs text-text-muted">{citation.loi}</p>
					</div>
				</div>
				<span className={cn("rounded-full px-2 py-0.5 text-[11px] font-semibold", tone)}>
					{label}
				</span>
			</header>
			<blockquote className="mt-3 text-sm leading-relaxed text-text-strong">
				« {citation.extrait} »
			</blockquote>
		</article>
	);
}
