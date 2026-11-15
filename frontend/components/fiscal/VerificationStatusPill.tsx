import { CheckCircle2, AlertTriangle, ShieldAlert, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { VerificationStatus } from "@/lib/types";

const META: Record<string, { label: string; Icon: typeof CheckCircle2; classes: string }> = {
	verifie: {
		label: "Vérifié",
		Icon: CheckCircle2,
		classes: "bg-success-badge text-success border-success/20",
	},
	partiel: {
		label: "Partiellement vérifié",
		Icon: AlertTriangle,
		classes: "bg-warning-badge text-warning border-warning/20",
	},
	non_verifie: {
		label: "Non vérifié",
		Icon: ShieldAlert,
		classes: "bg-error-badge text-danger border-danger/20",
	},
	incertain: {
		label: "Incertain",
		Icon: HelpCircle,
		classes: "bg-info-badge text-primary-700 border-primary-500/20",
	},
};

// Valeurs renvoyees par le backend (agents/verifier.py) -> cles d'affichage.
const BACKEND_STATUS: Record<string, string> = {
	validated: "verifie",
	rejected: "non_verifie",
};

export function VerificationStatusPill({
	status,
	className,
}: {
	status: VerificationStatus;
	className?: string;
}) {
	const meta = META[BACKEND_STATUS[status] ?? status] ?? META.incertain;
	const { Icon } = meta;
	return (
		<span
			role="status"
			aria-label={`Statut de vérification : ${meta.label}`}
			className={cn(
				"inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
				meta.classes,
				className,
			)}
		>
			<Icon className="h-3.5 w-3.5" aria-hidden />
			{meta.label}
		</span>
	);
}
