"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut, Mail, User as UserIcon, Languages } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { authStore } from "@/lib/auth";
import { RoleBadge } from "@/components/fiscal/RoleBadge";
import type { Language, User } from "@/lib/types";

function roleLabel(r: User["role"]) {
	return r === "citoyen" ? "Citoyen" : r === "avocat" ? "Avocat" : r === "juge" ? "Juge" : "Admin";
}

export default function ProfilePage() {
	const router = useRouter();
	const [user, setUser] = useState<User | null>(null);

	useEffect(() => {
		setUser(authStore.getUser());
	}, []);

	if (!user) return null;

	const updateLanguage = async (lang: Language) => {
		const previous = user;
		const next = { ...user, language: lang };
		authStore.setUser(next);
		setUser(next);
		try {
			await api.updateProfile({ preferred_lang: lang });
			toast.success("Langue mise à jour");
		} catch (err) {
			authStore.setUser(previous);
			setUser(previous);
			toast.error(err instanceof ApiError ? err.message : "Impossible de mettre à jour la langue");
		}
	};

	const handleLogout = () => {
		authStore.clear();
		router.push("/login");
	};

	return (
		<div className="mx-auto max-w-3xl space-y-6">
			<div className="surface-card p-6">
				<div className="flex flex-wrap items-start justify-between gap-4">
					<div className="flex items-center gap-4">
						<div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-900 text-lg font-bold text-white">
							{user.full_name
								.split(" ")
								.map((n) => n[0])
								.slice(0, 2)
								.join("")
								.toUpperCase()}
						</div>
						<div>
							<h2 className="font-display text-xl font-bold">{user.full_name}</h2>
							<p className="text-sm text-text-muted">{user.email}</p>
						</div>
					</div>
					<RoleBadge role={user.role} />
				</div>
			</div>

			<div className="grid gap-4 md:grid-cols-2">
				<InfoRow Icon={UserIcon} label="Identifiant" value={user.id} />
				<InfoRow Icon={Mail} label="E-mail" value={user.email} />
				<div className="surface-card p-4">
					<div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
						<Languages className="h-3.5 w-3.5" /> Langue préférée
					</div>
					<div className="mt-2">
						<Select value={user.language} onValueChange={(v) => updateLanguage(v as Language)}>
							<SelectTrigger className="w-full">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="fr">Français</SelectItem>
								<SelectItem value="ar">العربية (bientôt)</SelectItem>
							</SelectContent>
						</Select>
					</div>
				</div>
				<InfoRow Icon={UserIcon} label="Rôle" value={roleLabel(user.role)} />
			</div>

			<div className="surface-card p-6">
				<h3 className="font-display text-base font-semibold">Session</h3>
				<p className="mt-1 text-sm text-text-muted">
					Vous êtes actuellement connecté(e). La déconnexion effacera votre session locale.
				</p>
				<Button variant="outline" onClick={handleLogout} className="mt-4">
					<LogOut className="mr-2 h-4 w-4" /> Se déconnecter
				</Button>
			</div>
		</div>
	);
}

function InfoRow({
	Icon,
	label,
	value,
}: {
	Icon: typeof UserIcon;
	label: string;
	value: string;
}) {
	return (
		<div className="surface-card p-4">
			<div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
				<Icon className="h-3.5 w-3.5" /> {label}
			</div>
			<p className="mt-2 truncate text-sm font-medium text-text-strong">{value}</p>
		</div>
	);
}
