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

const schema = z
	.object({
		full_name: z.string().min(2, "Nom complet requis"),
		email: z.string().email("Adresse e-mail invalide"),
		password: z.string().min(8, "Au moins 8 caractères"),
		confirm: z.string(),
	})
	.refine((v) => v.password === v.confirm, {
		message: "Les mots de passe ne correspondent pas",
		path: ["confirm"],
	});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
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
			const res = await api.register({
				email: values.email,
				password: values.password,
				full_name: values.full_name,
			});
			authStore.setSession(res);
			toast.success("Compte créé avec succès");
			router.push("/chat");
		} catch (err) {
			const msg = err instanceof ApiError ? err.message : "Impossible de créer le compte";
			toast.error(msg);
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<AuthLayout
			title="Créer un compte citoyen"
			subtitle="Rejoignez FiscalMind en quelques secondes"
			footer={
				<>
					Vous avez déjà un compte ?{" "}
					<Link href="/login" className="font-semibold text-primary-700 hover:underline">
						Se connecter
					</Link>
				</>
			}
		>
			<form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
				<Field label="Nom complet" id="full_name" error={errors.full_name?.message}>
					<Input id="full_name" autoComplete="name" {...register("full_name")} />
				</Field>
				<Field label="Adresse e-mail" id="email" error={errors.email?.message}>
					<Input id="email" type="email" autoComplete="email" {...register("email")} />
				</Field>
				<Field label="Mot de passe" id="password" error={errors.password?.message}>
					<Input
						id="password"
						type="password"
						autoComplete="new-password"
						{...register("password")}
					/>
				</Field>
				<Field label="Confirmer le mot de passe" id="confirm" error={errors.confirm?.message}>
					<Input
						id="confirm"
						type="password"
						autoComplete="new-password"
						{...register("confirm")}
					/>
				</Field>
				<Button
					type="submit"
					disabled={submitting}
					className="w-full bg-primary-700 hover:bg-primary-900"
				>
					{submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Créer mon compte"}
				</Button>
			</form>
		</AuthLayout>
	);
}
