import { Sparkles, User as UserIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ChatMessage {
	id: string;
	role: "user" | "assistant";
	content: string;
}

export function MessageBubble({ message }: { message: ChatMessage }) {
	const isUser = message.role === "user";
	return (
		<div
			className={cn(
				"flex w-full gap-3 animate-slide-up",
				isUser ? "justify-end" : "justify-start",
			)}
		>
			{!isUser && (
				<div
					aria-hidden
					className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-900 text-white"
				>
					<Sparkles className="h-4 w-4" />
				</div>
			)}
			<div
				className={cn(
					"max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed shadow-sm",
					isUser
						? "bg-primary-700 text-primary-foreground rounded-tr-sm"
						: "bg-card border border-border-soft text-text-strong rounded-tl-sm",
				)}
			>
				{message.content.split("\n").map((line, i) => (
					<p key={i} className={cn(i > 0 && "mt-2")}>
						{line}
					</p>
				))}
			</div>
			{isUser && (
				<div
					aria-hidden
					className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-info-badge text-primary-700"
				>
					<UserIcon className="h-4 w-4" />
				</div>
			)}
		</div>
	);
}
