import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Manrope, Source_Sans_3 } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";

const sourceSans = Source_Sans_3({
	subsets: ["latin"],
	variable: "--font-source-sans",
	weight: ["400", "500", "600", "700"],
});

const manrope = Manrope({
	subsets: ["latin"],
	variable: "--font-manrope",
	weight: ["600", "700", "800"],
});

export const metadata: Metadata = {
	title: "FiscalMind — Loi de finance tunisienne, expliquée avec sources",
	description:
		"Interrogez la loi de finance tunisienne en langage naturel. Réponses vérifiées, citations d'articles, disclaimer légal — pensé pour citoyens, avocats et juges.",
};

type RootLayoutProps = {
	children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
	return (
		<html lang="fr" className={`${sourceSans.variable} ${manrope.variable}`}>
			<body>
				{children}
				<Toaster richColors position="top-right" closeButton />
			</body>
		</html>
	);
}
