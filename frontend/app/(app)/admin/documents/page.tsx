"use client";

import { useEffect, useRef, useState } from "react";
import { Upload, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/fiscal/states";
import type { AdminDocument } from "@/lib/types";

const STATUS_META: Record<AdminDocument["status"], { label: string; classes: string }> = {
	uploaded: { label: "Chargé", classes: "bg-info-badge text-primary-700" },
	processing: { label: "Traitement…", classes: "bg-warning-badge text-warning" },
	indexed: { label: "Indexé", classes: "bg-success-badge text-success" },
	failed: { label: "Échec", classes: "bg-error-badge text-danger" },
};

function formatSize(bytes: number) {
	if (bytes < 1024) return `${bytes} o`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
	return `${(bytes / 1024 / 1024).toFixed(1)} Mo`;
}

export default function AdminDocumentsPage() {
	const [docs, setDocs] = useState<AdminDocument[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [forbidden, setForbidden] = useState(false);
	const [uploading, setUploading] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const load = async () => {
		setLoading(true);
		setError(null);
		setForbidden(false);
		try {
			setDocs(await api.getDocuments());
		} catch (err) {
			if (err instanceof ApiError && err.status === 403) {
				setForbidden(true);
			} else {
				setError(err instanceof ApiError ? err.message : "Impossible de charger les documents");
			}
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		load();
	}, []);

	const onUpload = async (files: FileList | null) => {
		if (!files || files.length === 0) return;
		setUploading(true);
		let succeeded = 0;
		let failed = 0;
		for (const file of Array.from(files)) {
			try {
				const doc = await api.uploadDocument(file);
				setDocs((prev) => [doc, ...prev]);
				succeeded += 1;
			} catch (err) {
				failed += 1;
				const msg = err instanceof ApiError ? err.message : `Échec de l'envoi de ${file.name}`;
				toast.error(msg);
			}
		}
		setUploading(false);
		if (fileInputRef.current) fileInputRef.current.value = "";
		if (succeeded > 0) {
			toast.success(`${succeeded} document${succeeded > 1 ? "s" : ""} indexé${succeeded > 1 ? "s" : ""}`);
		}
		if (failed === 0 && succeeded > 0) return;
	};

	if (loading) {
		return (
			<div className="mx-auto max-w-6xl">
				<LoadingSkeleton lines={6} />
			</div>
		);
	}

	if (forbidden) {
		return (
			<div className="mx-auto max-w-6xl">
				<EmptyState
					title="Réservé aux administrateurs"
					description="Ton compte n'a pas les droits nécessaires pour gérer le corpus documentaire."
				/>
			</div>
		);
	}

	if (error) {
		return (
			<div className="mx-auto max-w-6xl">
				<ErrorState title="Documents indisponibles" description={error} onRetry={load} />
			</div>
		);
	}

	return (
		<div className="mx-auto max-w-6xl space-y-6">
			<div className="surface-card flex flex-wrap items-center justify-between gap-4 p-6">
				<div>
					<h2 className="font-display text-xl font-bold">Corpus documentaire</h2>
					<p className="text-sm text-text-muted">
						Textes officiels, lois de finance, circulaires et jurisprudence.
					</p>
				</div>
				<label className="inline-flex cursor-pointer">
					<input
						ref={fileInputRef}
						type="file"
						multiple
						className="sr-only"
						disabled={uploading}
						onChange={(e) => onUpload(e.target.files)}
						accept=".pdf,.txt,.md"
					/>
					<span
						className={cn(
							"inline-flex items-center gap-2 rounded-md bg-primary-700 px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary-900",
							uploading && "pointer-events-none opacity-70",
						)}
					>
						{uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
						Téléverser des documents
					</span>
				</label>
			</div>

			{docs.length === 0 ? (
				<EmptyState
					icon={<FileText className="h-6 w-6" />}
					title="Aucun document indexé"
					description="Téléverse un PDF, un .txt ou un .md pour l'ajouter au corpus."
				/>
			) : (
				<div className="surface-card overflow-hidden">
					<Table>
						<TableHeader>
							<TableRow>
								<TableHead>Document</TableHead>
								<TableHead>Taille</TableHead>
								<TableHead>Ajouté le</TableHead>
								<TableHead>Statut</TableHead>
							</TableRow>
						</TableHeader>
						<TableBody>
							{docs.map((d) => {
								const meta = STATUS_META[d.status];
								return (
									<TableRow key={d.id}>
										<TableCell>
											<div className="flex items-center gap-2">
												<FileText className="h-4 w-4 text-primary-700" aria-hidden />
												<span className="font-medium">{d.filename}</span>
											</div>
											{typeof d.chunks === "number" && d.chunks > 0 && (
												<p className="mt-0.5 text-xs text-text-muted">{d.chunks} segments indexés</p>
											)}
											{d.error && <p className="mt-0.5 text-xs text-danger">{d.error}</p>}
										</TableCell>
										<TableCell className="text-sm text-text-muted">
											{formatSize(d.size_bytes)}
										</TableCell>
										<TableCell className="text-sm text-text-muted">
											{new Date(d.uploaded_at).toLocaleDateString("fr-FR")}
										</TableCell>
										<TableCell>
											<span
												className={cn(
													"inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold",
													meta.classes,
												)}
											>
												{meta.label}
											</span>
										</TableCell>
									</TableRow>
								);
							})}
						</TableBody>
					</Table>
				</div>
			)}
		</div>
	);
}
