"use client";

import { useState } from "react";
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

const PREVIEW_CHARS = 420;

// Les PDF (formulaires, notes) contiennent de longues lignes de pointilles a
// remplir : on les reduit pour qu'elles ne cassent pas la mise en page.
function cleanExtract(text: string): string {
	return text
		.replace(/[.…·_]{6,}/g, " … ")
		.replace(/\s{2,}/g, " ")
		.trim();
}

export function CitationCard({ citation, className }: { citation: Citation; className?: string }) {
	const [expanded, setExpanded] = useState(false);
	const label = STATUT_LABEL[citation.statut] ?? citation.statut;
	const tone = STATUT_TONE[citation.statut] ?? "bg-info-badge text-primary-700";
	// numero_article = 0 : aucun numero d'article detecte (notes communes, etc.).
	const title = citation.numero_article > 0 ? `Article ${citation.numero_article}` : "Extrait";

	const extract = cleanExtract(citation.extrait);
	const isLong = extract.length > PREVIEW_CHARS;
	const shown = expanded || !isLong ? extract : `${extract.slice(0, PREVIEW_CHARS).trimEnd()}…`;

	return (
		<article
			className={cn("legal-citation surface-card min-w-0 p-4 animate-fade-in", className)}
			aria-label={`Citation : ${title}, ${citation.loi}`}
		>
			<header className="flex flex-wrap items-start justify-between gap-2">
				<div className="flex min-w-0 items-start gap-2">
					<BookMarked className="mt-0.5 h-4 w-4 shrink-0 text-primary-700" aria-hidden />
					<div className="min-w-0">
						<h4 className="text-sm font-semibold text-text-strong">{title}</h4>
						<p className="break-words text-xs text-text-muted [overflow-wrap:anywhere]">{citation.loi}</p>
					</div>
				</div>
				<span className={cn("rounded-full px-2 py-0.5 text-[11px] font-semibold", tone)}>{label}</span>
			</header>
			<blockquote className="mt-3 break-words text-sm leading-relaxed text-text-strong [overflow-wrap:anywhere]">
				« {shown} »
			</blockquote>
			{isLong && (
				<button
					type="button"
					onClick={() => setExpanded((v) => !v)}
					className="mt-2 text-xs font-semibold text-primary-700 hover:underline"
					aria-expanded={expanded}
				>
					{expanded ? "Afficher moins" : "Afficher plus"}
				</button>
			)}
		</article>
	);
}
