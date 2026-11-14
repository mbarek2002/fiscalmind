import Link from "next/link";

export default function NotFound() {
	return (
		<div className="flex min-h-dvh items-center justify-center bg-background px-4">
			<div className="max-w-md text-center">
				<p className="font-display text-sm font-semibold uppercase tracking-widest text-primary-700">
					FiscalMind
				</p>
				<h1 className="mt-2 font-display text-7xl font-bold text-primary-900">404</h1>
				<h2 className="mt-4 text-xl font-semibold">Page introuvable</h2>
				<p className="mt-2 text-sm text-text-muted">
					La page que vous recherchez n&apos;existe pas ou a été déplacée.
				</p>
				<div className="mt-6">
					<Link
						href="/"
						className="inline-flex items-center justify-center rounded-md bg-primary-700 px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-900"
					>
						Retour à l&apos;accueil
					</Link>
				</div>
			</div>
		</div>
	);
}
