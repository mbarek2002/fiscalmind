"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { authStore } from "@/lib/auth";
import { AuthLayout, Field } from "@/components/fiscal/AuthLayout";

const schema = z.object({
	email: z.string().email("Adresse e-mail invalide"),
	password: z.string().min(6, "Au moins 6 caractères"),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
	const router = useRouter();
	const [submitting, setSubmitting] = useState(false);
	const {
		register,
		handleSubmit,
		formState: { errors },
	} = useForm<FormValues>({ resolver: zodResolver(schema) });

	const onSubmit = async (values: FormValues) => {
		setSubmitting(true);
		try {
			const res = await api.login(values.email, values.password);
			authStore.setSession(res);
			toast.success("Connexion réussie");
			router.push("/chat");
		} catch (err) {
			const msg = err instanceof ApiError ? err.message : "Impossible de se connecter";
			toast.error(msg);
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<AuthLayout
			title="Se connecter"
			subtitle="Accédez à votre espace FiscalMind"
			footer={
				<>
					Pas encore de compte ?{" "}
					<Link href="/register" className="font-semibold text-primary-700 hover:underline">
						Créer un compte citoyen
					</Link>
				</>
			}
		>
			<form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
				<Field label="Adresse e-mail" id="email" error={errors.email?.message}>
					<Input
						id="email"
						type="email"
						autoComplete="email"
						placeholder="prenom.nom@exemple.tn"
						aria-invalid={!!errors.email}
						{...register("email")}
					/>
				</Field>
				<Field label="Mot de passe" id="password" error={errors.password?.message}>
					<Input
						id="password"
						type="password"
						autoComplete="current-password"
						aria-invalid={!!errors.password}
						{...register("password")}
					/>
				</Field>
				<Button
					type="submit"
					disabled={submitting}
					className="w-full bg-primary-700 hover:bg-primary-900"
				>
					{submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Se connecter"}
				</Button>
			</form>
		</AuthLayout>
	);
}
