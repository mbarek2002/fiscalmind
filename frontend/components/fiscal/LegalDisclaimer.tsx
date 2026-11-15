import { ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export function LegalDisclaimer({ text, className }: { text?: string; className?: string }) {
	return (
		<aside
			role="note"
			className={cn(
				"flex items-start gap-2 rounded-lg border border-warning/30 bg-warning-badge px-3 py-2 text-xs text-text-strong",
				className,
			)}
		>
			<ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
			<p className="leading-relaxed">
				{text ??
					"Ceci ne remplace pas un avis juridique officiel. Les réponses sont générées à titre informatif."}
			</p>
		</aside>
	);
}
