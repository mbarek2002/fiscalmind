import type { AdminDocument, QueryResponse } from "./types";

export const LEGAL_DISCLAIMER =
	"Ceci ne remplace pas un avis juridique officiel. Les réponses sont générées à titre informatif à partir de la loi de finance tunisienne.";

export function mockQueryResponse(question: string): QueryResponse {
	return {
		query_id: crypto.randomUUID(),
		question,
		created_at: new Date().toISOString(),
		final_answer:
			"D'après la loi de finance tunisienne en vigueur, le régime applicable prévoit une imposition progressive selon les tranches définies à l'article 44 du Code de l'IRPP. Les contribuables relevant du régime réel doivent déposer leur déclaration annuelle avant le 25 du quatrième mois suivant la clôture de l'exercice. Des dispositions spécifiques s'appliquent aux revenus exceptionnels et aux plus-values immobilières.",
		verification_status: "verifie",
		disclaimer: LEGAL_DISCLAIMER,
		citations: [
			{
				article_id: "art-44-irpp",
				loi: "Code de l'Impôt sur le Revenu (IRPP)",
				numero_article: 44,
				statut: "en_vigueur",
				langue: "fr",
				extrait:
					"Le taux de l'impôt est déterminé selon le barème progressif prévu au tableau annexé au présent code, appliqué au revenu net global du contribuable.",
			},
			{
				article_id: "art-60-lf-2024",
				loi: "Loi de finances 2024",
				numero_article: 60,
				statut: "en_vigueur",
				langue: "fr",
				extrait:
					"Les personnes physiques soumises au régime réel sont tenues de déposer leur déclaration annuelle avant le 25 du quatrième mois suivant la clôture de l'exercice concerné.",
			},
		],
	};
}

export const mockHistory: QueryResponse[] = [
	{
		...mockQueryResponse("Quel est le délai de dépôt de la déclaration annuelle IRPP ?"),
		query_id: "hist-1",
		created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
	},
	{
		...mockQueryResponse("Comment sont imposées les plus-values immobilières en 2024 ?"),
		query_id: "hist-2",
		verification_status: "partiel",
		created_at: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
	},
	{
		...mockQueryResponse("Quelles sont les obligations TVA d'un consultant indépendant ?"),
		query_id: "hist-3",
		created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
	},
];

export const mockDocuments: AdminDocument[] = [
	{
		id: "doc-1",
		filename: "loi-finances-2024.pdf",
		size_bytes: 3_540_212,
		uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
		status: "indexed",
		chunks: 842,
	},
	{
		id: "doc-2",
		filename: "code-irpp-consolide.pdf",
		size_bytes: 5_120_998,
		uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
		status: "processing",
		chunks: 0,
	},
	{
		id: "doc-3",
		filename: "circulaire-tva-2024-03.pdf",
		size_bytes: 812_334,
		uploaded_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
		status: "uploaded",
	},
	{
		id: "doc-4",
		filename: "jurisprudence-tribunal-admin-2023.pdf",
		size_bytes: 2_430_112,
		uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 9).toISOString(),
		status: "failed",
	},
];
