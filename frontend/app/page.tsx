import Link from "next/link";
import {
	ArrowRight,
	Activity,
	ShieldCheck,
	BookOpen,
	Sparkles,
	Scale,
	Gavel,
	User as UserIcon,
	Landmark,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LegalDisclaimer } from "@/components/fiscal/LegalDisclaimer";

const PROFILES = [
	{
		Icon: UserIcon,
		title: "Citoyen",
		desc: "Comprendre ses obligations fiscales sans jargon, en français clair.",
	},
	{
		Icon: Scale,
		title: "Avocat",
		desc: "Accéder rapidement aux articles pertinents et à la jurisprudence.",
	},
	{
		Icon: Gavel,
		title: "Juge",
		desc: "Vérifier les textes en vigueur avec citations sourcées et traçables.",
	},
];

const BENEFITS = [
	{
		Icon: ShieldCheck,
		title: "Réponses vérifiées",
		desc: "Chaque réponse est accompagnée d'un statut de vérification et de citations d'articles.",
	},
	{
		Icon: BookOpen,
		title: "Sources traçables",
		desc: "Références directes à la loi de finance, aux codes fiscaux et à la jurisprudence.",
	},
	{
		Icon: Sparkles,
		title: "Recherche augmentée (RAG)",
		desc: "Une IA appuyée sur les textes officiels indexés, pas sur des suppositions.",
	},
];

export default function Landing() {
	return (
		<div className="min-h-dvh">
			{/* Header */}
			<header className="border-b border-border-soft bg-card/70 backdrop-blur">
				<div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 lg:px-8">
					<div className="flex items-center gap-2">
						<span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary-900 text-white">
							<Landmark className="h-5 w-5" aria-hidden />
						</span>
						<div>
							<p className="font-display text-base font-bold leading-none">FiscalMind</p>
							<p className="text-[11px] text-text-muted">Loi de finance · Tunisie</p>
						</div>
					</div>
					<nav className="flex items-center gap-2">
						<Link href="/health">
							<Button variant="ghost" size="sm" className="text-text-muted">
								<Activity className="mr-1.5 h-4 w-4" /> Santé système
							</Button>
						</Link>
						<Link href="/login">
							<Button variant="ghost" size="sm">
								Se connecter
							</Button>
						</Link>
						<Link href="/register">
							<Button size="sm" className="bg-primary-700 hover:bg-primary-900">
								S&apos;inscrire
							</Button>
						</Link>
					</nav>
				</div>
			</header>

			{/* Hero */}
			<section className="mx-auto max-w-6xl px-4 py-16 lg:px-8 lg:py-24">
				<div className="grid gap-10 lg:grid-cols-2 lg:items-center">
					<div className="animate-fade-in">
						<span className="inline-flex items-center gap-1.5 rounded-full bg-info-badge px-3 py-1 text-xs font-semibold text-primary-700">
							<ShieldCheck className="h-3.5 w-3.5" /> Assistant juridique sourcé
						</span>
						<h1 className="mt-4 font-display text-4xl font-bold leading-tight text-primary-900 sm:text-5xl">
							La loi de finance tunisienne, expliquée avec sources.
						</h1>
						<p className="mt-4 max-w-xl text-base leading-relaxed text-text-muted sm:text-lg">
							FiscalMind est un assistant juridique augmenté par la recherche (RAG) dédié à la
							fiscalité tunisienne. Pensé pour les citoyens, les avocats et les juges, il fournit
							des réponses vérifiées, accompagnées de citations d&apos;articles.
						</p>
						<div className="mt-8 flex flex-wrap gap-3">
							<Link href="/register">
								<Button size="lg" className="bg-primary-700 hover:bg-primary-900">
									Commencer <ArrowRight className="ml-2 h-4 w-4" />
								</Button>
							</Link>
							<Link href="/health">
								<Button size="lg" variant="outline">
									<Activity className="mr-2 h-4 w-4" /> Tester la santé backend
								</Button>
							</Link>
						</div>
						<LegalDisclaimer className="mt-8 max-w-lg" />
					</div>

					<div className="surface-card animate-slide-up p-6 lg:p-8">
						<div className="flex items-center gap-2 border-b border-border-soft pb-3">
							<span className="h-2.5 w-2.5 rounded-full bg-danger" />
							<span className="h-2.5 w-2.5 rounded-full bg-warning" />
							<span className="h-2.5 w-2.5 rounded-full bg-success" />
							<span className="ml-2 text-xs text-text-faint">consultation.fiscalmind.tn</span>
						</div>
						<div className="mt-4 space-y-3">
							<div className="ml-auto max-w-[80%] rounded-xl bg-primary-700 px-4 py-2.5 text-sm text-white shadow-sm">
								Quel est le délai de dépôt de la déclaration IRPP&nbsp;?
							</div>
							<div className="max-w-[85%] rounded-xl border border-border-soft bg-card px-4 py-3 text-sm">
								<p>
									Les personnes physiques soumises au régime réel doivent déposer leur déclaration
									avant le <strong>25 du 4ᵉ mois</strong> suivant la clôture de l&apos;exercice.
								</p>
								<div className="legal-citation mt-3 rounded-r-md p-2 text-xs">
									<p className="font-semibold">Article 60 — Loi de finances 2024</p>
									<p className="text-text-muted">En vigueur · Français</p>
								</div>
							</div>
							<div className="flex items-center gap-2 text-xs text-text-muted">
								<span className="inline-flex items-center gap-1 rounded-full bg-success-badge px-2 py-0.5 font-semibold text-success">
									<ShieldCheck className="h-3 w-3" /> Vérifié
								</span>
								Réponse basée sur 2 citations
							</div>
						</div>
					</div>
				</div>
			</section>

			{/* Benefits */}
			<section className="border-y border-border-soft bg-card/60">
				<div className="mx-auto max-w-6xl px-4 py-16 lg:px-8">
					<h2 className="font-display text-2xl font-bold sm:text-3xl">
						Une plateforme pensée pour la rigueur
					</h2>
					<p className="mt-2 max-w-2xl text-text-muted">
						FiscalMind combine la précision du droit et la clarté d&apos;une interface institutionnelle.
					</p>
					<div className="mt-8 grid gap-4 md:grid-cols-3">
						{BENEFITS.map(({ Icon, title, desc }) => (
							<div key={title} className="surface-card p-6">
								<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info-badge text-primary-700">
									<Icon className="h-5 w-5" />
								</div>
								<h3 className="mt-4 text-base font-semibold">{title}</h3>
								<p className="mt-1 text-sm text-text-muted">{desc}</p>
							</div>
						))}
					</div>
				</div>
			</section>

			{/* Profiles */}
			<section className="mx-auto max-w-6xl px-4 py-16 lg:px-8">
				<h2 className="font-display text-2xl font-bold sm:text-3xl">Trois profils, un même outil</h2>
				<p className="mt-2 max-w-2xl text-text-muted">
					Chaque profil bénéficie d&apos;une expérience adaptée à son niveau de lecture juridique.
				</p>
				<div className="mt-8 grid gap-4 md:grid-cols-3">
					{PROFILES.map(({ Icon, title, desc }) => (
						<div key={title} className="surface-card p-6">
							<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-900 text-white">
								<Icon className="h-5 w-5" />
							</div>
							<h3 className="mt-4 font-display text-lg font-semibold">{title}</h3>
							<p className="mt-1 text-sm text-text-muted">{desc}</p>
						</div>
					))}
				</div>
			</section>

			{/* Footer */}
			<footer className="border-t border-border-soft bg-card/70">
				<div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-text-muted lg:flex-row lg:items-center lg:justify-between lg:px-8">
					<p>© {new Date().getFullYear()} FiscalMind — Assistant juridique fiscal.</p>
					<p>
						FiscalMind ne remplace pas un avis juridique officiel. Vérifiez toujours auprès d&apos;un
						professionnel.
					</p>
				</div>
			</footer>
		</div>
	);
}
