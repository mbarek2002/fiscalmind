"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { Send, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MessageBubble, type ChatMessage } from "@/components/fiscal/MessageBubble";
import { CitationCard } from "@/components/fiscal/CitationCard";
import { VerificationStatusPill } from "@/components/fiscal/VerificationStatusPill";
import { LegalDisclaimer } from "@/components/fiscal/LegalDisclaimer";
import { LoadingSkeleton, EmptyState } from "@/components/fiscal/states";
import { api, ApiError } from "@/lib/api";
import type { QueryResponse } from "@/lib/types";

export default function ChatPage() {
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [current, setCurrent] = useState<QueryResponse | null>(null);
	const [loading, setLoading] = useState(false);
	const [input, setInput] = useState("");
	const textareaRef = useRef<HTMLTextAreaElement>(null);

	const submit = async () => {
		const q = input.trim();
		if (!q || loading) return;
		setInput("");
		setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: q }]);
		setLoading(true);
		setCurrent(null);
		try {
			const res = await api.query({ question: q, language: "fr" });
			setMessages((prev) => [
				...prev,
				{ id: res.query_id, role: "assistant", content: res.final_answer },
			]);
			setCurrent(res);
		} catch (err) {
			const msg = err instanceof ApiError ? err.message : "Erreur lors de la consultation";
			toast.error(msg);
		} finally {
			setLoading(false);
		}
	};

	const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			submit();
		}
	};

	return (
		<div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
			<section className="flex min-h-[70dvh] flex-col">
				<div className="surface-card flex-1 space-y-4 p-4 lg:p-6">
					{messages.length === 0 && !loading && (
						<EmptyState
							icon={<Sparkles className="h-6 w-6" />}
							title="Posez votre première question"
							description="Ex : « Quel est le délai de dépôt de la déclaration IRPP en régime réel ? »"
						/>
					)}
					{messages.map((m) => (
						<MessageBubble key={m.id} message={m} />
					))}
					{loading && (
						<div className="max-w-[85%]">
							<LoadingSkeleton lines={4} />
						</div>
					)}
				</div>

				<form
					onSubmit={(e) => {
						e.preventDefault();
						submit();
					}}
					className="surface-card mt-4 flex items-end gap-2 p-3"
				>
					<label htmlFor="question" className="sr-only">
						Votre question
					</label>
					<Textarea
						id="question"
						ref={textareaRef}
						rows={2}
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={onKey}
						placeholder="Posez une question sur la loi de finance tunisienne…"
						className="min-h-[48px] resize-none border-none bg-transparent focus-visible:ring-0"
					/>
					<Button
						type="submit"
						disabled={!input.trim() || loading}
						className="bg-primary-700 hover:bg-primary-900"
						aria-label="Envoyer la question"
					>
						<Send className="h-4 w-4" />
					</Button>
				</form>
				<LegalDisclaimer className="mt-3" />
			</section>

			<aside className="space-y-4">
				<div className="surface-card p-4">
					<h2 className="font-display text-sm font-bold uppercase tracking-wide text-text-muted">
						Vérification
					</h2>
					{current ? (
						<div className="mt-2 space-y-2">
							<VerificationStatusPill status={current.verification_status} />
							<p className="text-xs text-text-muted">
								{current.citations.length} citation{current.citations.length > 1 ? "s" : ""} sourcée
								{current.citations.length > 1 ? "s" : ""}.
							</p>
						</div>
					) : (
						<p className="mt-2 text-xs text-text-muted">
							Le statut de vérification s&apos;affichera après votre première réponse.
						</p>
					)}
				</div>

				<div>
					<h2 className="mb-2 font-display text-sm font-bold uppercase tracking-wide text-text-muted">
						Citations
					</h2>
					{current && current.citations.length > 0 ? (
						<div className="space-y-3">
							{current.citations.map((c) => (
								<CitationCard key={c.article_id} citation={c} />
							))}
						</div>
					) : (
						<div className="surface-card p-4 text-xs text-text-muted">
							Aucune citation à afficher pour le moment.
						</div>
					)}
				</div>
			</aside>
		</div>
	);
}
