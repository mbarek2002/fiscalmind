import Link from "next/link";

export default function HomePage() {
	return (
		<main>
			<h1>FiscalMind Frontend</h1>
			<p className="muted">
				Socle Next.js minimal prêt. Utilise la page de test pour vérifier la connexion backend.
			</p>

			<div className="card">
				<h2>Tests rapides</h2>
				<ul>
					<li>
						<Link href="/health-test">Tester le endpoint backend /health</Link>
					</li>
				</ul>
			</div>
		</main>
	);
}
