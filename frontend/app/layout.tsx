import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
	title: "FiscalMind",
	description: "Agentic Hybrid RAG - Loi de finance tunisienne",
};

type RootLayoutProps = {
	children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
	return (
		<html lang="fr">
			<body>{children}</body>
		</html>
	);
}
