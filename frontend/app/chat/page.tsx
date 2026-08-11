"use client";

import { FormEvent, useState } from "react";

import { postQuery, type QueryResponse } from "../../lib/api-client";

export default function ChatPage() {
	const [question, setQuestion] = useState("");
	const [accessToken, setAccessToken] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [result, setResult] = useState<QueryResponse | null>(null);

	async function handleSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setError(null);
		setResult(null);

		if (question.trim().length < 3) {
			setError("La question doit contenir au moins 3 caracteres.");
			return;
		}

		setLoading(true);
		try {
			const response = await postQuery({
				question: question.trim(),
				language: "fr",
			}, accessToken.trim() || undefined);
			setResult(response);
		} catch (err) {
			const message = err instanceof Error ? err.message : "Unknown error";
			setError(message);
		} finally {
			setLoading(false);
		}
	}

	return (
		<main>
			<h1>Chat FiscalMind (Mock)</h1>
			<p className="muted">
				Premier flux dev: formulaire frontend connecte a l&apos;endpoint backend
				 /api/v1/query.
			</p>

			<div className="card">
				<form onSubmit={handleSubmit}>
					<label htmlFor="token">Access token (JWT)</label>
					<input
						id="token"
						value={accessToken}
						onChange={(e) => setAccessToken(e.target.value)}
						placeholder="Colle ici le access_token retourne par /api/v1/auth/login"
						style={{ width: "100%", marginTop: "0.5rem", marginBottom: "0.75rem" }}
					/>

					<label htmlFor="question">Votre question</label>
					<textarea
						id="question"
						value={question}
						onChange={(e) => setQuestion(e.target.value)}
						placeholder="Ex: Quelle sanction pour une non-declaration de TVA en 2023 ?"
						rows={5}
						style={{ width: "100%", marginTop: "0.5rem" }}
					/>
					<button
						type="submit"
						disabled={loading}
						style={{ marginTop: "0.75rem" }}
					>
						{loading ? "Envoi..." : "Envoyer"}
					</button>
				</form>
			</div>

			{error ? (
				<div className="card" style={{ marginTop: "1rem", borderColor: "#ef4444" }}>
					<strong>Erreur</strong>
					<p>{error}</p>
				</div>
			) : null}

			{result ? (
				<div className="card" style={{ marginTop: "1rem" }}>
					<h2>Reponse backend</h2>
					<p>
						<strong>query_id:</strong> {result.query_id}
					</p>
					<p>
						<strong>verification_status:</strong> {result.verification_status}
					</p>
					<p>
						<strong>answer:</strong> {result.final_answer}
					</p>
					<h3>Citations</h3>
					{result.citations.length === 0 ? (
						<p className="muted">Aucune citation retournee pour cette question.</p>
					) : (
						<ul>
							{result.citations.map((citation) => (
								<li key={`${citation.article_id}-${citation.langue}`}>
									{citation.loi} - Article {citation.numero_article} ({citation.statut})
								</li>
							))}
						</ul>
					)}
					<p className="muted">{result.disclaimer}</p>
				</div>
			) : null}
		</main>
	);
}
