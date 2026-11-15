"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
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
import { authStore, CHAT_KEY_PREFIX } from "@/lib/auth";
import type { QueryResponse } from "@/lib/types";

interface ChatSnapshot {
	messages: ChatMessage[];
	current: QueryResponse | null;
}

// Conversation conservee pour la duree de l'onglet (sessionStorage) : survit au
// changement de page et au rechargement, effacee a la deconnexion (authStore.clear).
function chatStorageKey(): string {
	return CHAT_KEY_PREFIX + (authStore.getUser()?.id ?? "anonymous");
}

function loadChat(): ChatSnapshot | null {
	try {
		const raw = window.sessionStorage.getItem(chatStorageKey());
		return raw ? (JSON.parse(raw) as ChatSnapshot) : null;
	} catch {
		return null;
	}
}

function saveChat(snapshot: ChatSnapshot) {
	try {
		window.sessionStorage.setItem(chatStorageKey(), JSON.stringify(snapshot));
	} catch {
		// stockage plein ou indisponible : la conversation reste en memoire
	}
}

export default function ChatPage() {
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [current, setCurrent] = useState<QueryResponse | null>(null);
	const [loading, setLoading] = useState(false);
	const [input, setInput] = useState("");
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	const messagesEndRef = useRef<HTMLDivElement>(null);
	const citationsRef = useRef<HTMLDivElement>(null);
	const [restored, setRestored] = useState(false);

	// Restauration apres le montage (pas pendant le rendu serveur : evite un ecart d'hydratation).
	useEffect(() => {
		const saved = loadChat();
		if (saved) {
			setMessages(saved.messages);
			setCurrent(saved.current);
		}
		setRestored(true);
	}, []);
	useEffect(() => {
		if (restored) saveChat({ messages, current });
	}, [restored, messages, current]);

	// Suit le dernier message ; remet les citations en haut a chaque nouvelle reponse.
	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
	}, [messages, loading]);
	useEffect(() => {
		citationsRef.current?.scrollTo({ top: 0 });
	}, [current]);

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
		// Ecran large : la page tient dans la hauteur de <main> ; seules la conversation
		// et la liste des citations defilent. Petit ecran : empilement classique.
		<div className="mx-auto grid max-w-6xl gap-6 lg:h-full lg:grid-cols-[minmax(0,1fr)_320px] lg:grid-rows-[minmax(0,1fr)]">
			<section className="flex min-h-0 flex-col">
				<div className="surface-card min-h-[60dvh] flex-1 space-y-4 overflow-y-auto p-4 lg:min-h-0 lg:p-6">
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
					<div ref={messagesEndRef} aria-hidden />
				</div>

				<form
					onSubmit={(e) => {
						e.preventDefault();
						submit();
					}}
					className="surface-card mt-4 flex shrink-0 items-end gap-2 p-3"
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
				<LegalDisclaimer className="mt-3 shrink-0" />
			</section>

			<aside className="flex min-h-0 min-w-0 flex-col gap-4">
				<div className="surface-card shrink-0 p-4">
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

				<div className="flex min-h-0 flex-1 flex-col">
					<h2 className="mb-2 shrink-0 font-display text-sm font-bold uppercase tracking-wide text-text-muted">
						Citations
					</h2>
					{current && current.citations.length > 0 ? (
						<div
							ref={citationsRef}
							className="min-h-0 flex-1 space-y-3 overflow-y-auto overflow-x-hidden pr-1"
						>
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
