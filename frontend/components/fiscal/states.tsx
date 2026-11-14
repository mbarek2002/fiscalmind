import { AlertOctagon, Inbox, RefreshCcw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function EmptyState({
	title,
	description,
	icon,
	action,
	className,
}: {
	title: string;
	description?: string;
	icon?: ReactNode;
	action?: ReactNode;
	className?: string;
}) {
	return (
		<div
			className={cn(
				"surface-card flex flex-col items-center justify-center gap-3 p-10 text-center animate-fade-in",
				className,
			)}
		>
			<div className="rounded-full bg-info-badge p-3 text-primary-700">
				{icon ?? <Inbox className="h-6 w-6" aria-hidden />}
			</div>
			<h3 className="text-base font-semibold">{title}</h3>
			{description && <p className="max-w-sm text-sm text-text-muted">{description}</p>}
			{action}
		</div>
	);
}

export function ErrorState({
	title = "Une erreur est survenue",
	description,
	onRetry,
	className,
}: {
	title?: string;
	description?: string;
	onRetry?: () => void;
	className?: string;
}) {
	return (
		<div
			role="alert"
			className={cn(
				"surface-card flex flex-col items-center justify-center gap-3 p-8 text-center border-danger/20",
				className,
			)}
		>
			<div className="rounded-full bg-error-badge p-3 text-danger">
				<AlertOctagon className="h-6 w-6" aria-hidden />
			</div>
			<h3 className="text-base font-semibold text-text-strong">{title}</h3>
			{description && <p className="max-w-sm text-sm text-text-muted">{description}</p>}
			{onRetry && (
				<Button variant="outline" size="sm" onClick={onRetry}>
					<RefreshCcw className="mr-2 h-4 w-4" /> Réessayer
				</Button>
			)}
		</div>
	);
}

export function LoadingSkeleton({ lines = 3, className }: { lines?: number; className?: string }) {
	return (
		<div className={cn("surface-card space-y-3 p-4", className)} aria-busy="true" aria-live="polite">
			<Skeleton className="h-4 w-1/3" />
			{Array.from({ length: lines }).map((_, i) => (
				<Skeleton key={i} className={cn("h-3", i === lines - 1 ? "w-2/3" : "w-full")} />
			))}
		</div>
	);
}
