import { Gavel, Scale, ShieldCheck, User as UserIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/lib/types";

const ROLE_META: Record<UserRole, { label: string; Icon: typeof UserIcon; tone: string }> = {
	citoyen: { label: "Citoyen", Icon: UserIcon, tone: "bg-info-badge text-primary-700" },
	avocat: { label: "Avocat", Icon: Scale, tone: "bg-success-badge text-success" },
	juge: { label: "Juge", Icon: Gavel, tone: "bg-warning-badge text-warning" },
	admin: { label: "Admin", Icon: ShieldCheck, tone: "bg-primary-900 text-white" },
};

export function RoleBadge({ role, className }: { role: UserRole; className?: string }) {
	const { label, Icon, tone } = ROLE_META[role];
	return (
		<span
			className={cn(
				"inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
				tone,
				className,
			)}
		>
			<Icon className="h-3.5 w-3.5" aria-hidden />
			{label}
		</span>
	);
}
