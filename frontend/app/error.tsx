"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
	useEffect(() => {
		console.error(error);
	}, [error]);

	return (
		<div className="flex min-h-dvh items-center justify-center bg-background px-4">
			<div className="max-w-md text-center">
				<h1 className="text-xl font-semibold tracking-tight">Cette page n&apos;a pas pu se charger</h1>
				<p className="mt-2 text-sm text-text-muted">
					Une erreur est survenue. Vous pouvez réessayer ou revenir à l&apos;accueil.
				</p>
				<div className="mt-6 flex flex-wrap justify-center gap-2">
					<button
						onClick={reset}
						className="inline-flex items-center justify-center rounded-md bg-primary-700 px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-900"
					>
						Réessayer
					</button>
					<a
						href="/"
						className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
					>
						Accueil
					</a>
				</div>
			</div>
		</div>
	);
}
