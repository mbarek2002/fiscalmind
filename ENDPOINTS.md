# Spécification des endpoints API

Ce document liste l'ensemble des endpoints REST nécessaires au projet, regroupés par domaine fonctionnel. Base URL : `/api/v1`. Authentification : Bearer JWT (sauf `/auth/login` et `/health`). Rôles : `citoyen`, `avocat`, `juge`, `admin`, `entreprise`.

> **Rôle principal (2026-09-09)** : `entreprise` est le rôle central du système — voir [ARCHITECTURE.md — section 1](./ARCHITECTURE.md#1-objectif-du-projet). Les sections 3bis et 3ter ci-dessous (`/companies`, `/financial-submissions`) portent le cas d'usage réel. Les sections 3, 5, 6 (`/query`, `/articles`, `/jurisprudence`) restent documentées pour les profils secondaires avocat/juge/citoyen.

Référence croisée : implémentation prévue dans `backend/app/api/v1/endpoints/` (voir [STRUCTURE.md](./STRUCTURE.md)).

---

## 1. Authentification (`/auth`)

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| POST | `/auth/register` | `admin` | Crée un compte (avocat/juge/citoyen). Un citoyen peut aussi s'auto-inscrire si activé. |
| POST | `/auth/login` | public | Authentifie l'utilisateur, retourne un token JWT (access + refresh). |
| POST | `/auth/refresh` | authentifié | Renouvelle un access token à partir du refresh token. |
| POST | `/auth/logout` | authentifié | Invalide le refresh token courant. |

**Exemple `POST /auth/login`**
```json
// Requête
{ "email": "avocat@example.tn", "password": "********" }

// Réponse
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "u_123", "role": "avocat", "full_name": "..." }
}
```

---

## 2. Utilisateurs (`/users`)

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| GET | `/users/me` | authentifié | Profil de l'utilisateur courant. |
| PATCH | `/users/me` | authentifié | Mise à jour du profil (nom, préférences de langue). |
| GET | `/users` | `admin` | Liste paginée des utilisateurs (filtre par rôle). |
| GET | `/users/{user_id}` | `admin` | Détail d'un utilisateur. |
| PATCH | `/users/{user_id}/role` | `admin` | Modifie le rôle d'un utilisateur. |
| DELETE | `/users/{user_id}` | `admin` | Désactive/supprime un compte. |

---

## 3. Requête RAG principale (`/query`)

Cœur du système : déclenche le graphe multi-agents (LangGraph).

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| POST | `/query` | `avocat`, `juge`, `citoyen` | Soumet une question/un fait, exécute le pipeline agents complet, retourne la réponse formatée + citations. |
| GET | `/query/history` | authentifié | Historique des requêtes de l'utilisateur courant. |
| GET | `/query/{query_id}` | authentifié (propriétaire) ou `admin` | Détail d'une requête passée (réponse, sources, statut de vérification). |
| POST | `/query/{query_id}/feedback` | authentifié | Envoie un retour (pertinent/non pertinent, correction) sur une réponse — alimente l'amélioration continue. |
| GET | `/query/{query_id}/trace` | `admin` | Trace détaillée d'exécution des agents (lien vers Langfuse, latences, étapes de la boucle de vérification). |

**Exemple `POST /query`**
```json
// Requête
{
  "question": "Un contribuable n'a pas déclaré une partie de son chiffre d'affaires soumis à la TVA sur l'exercice 2023, quelle sanction risque-t-il ?",
  "language": "fr"
}

// Réponse
{
  "query_id": "q_456",
  "final_answer": "...",
  "citations": [
    {
      "article_id": "lf2023_art45",
      "loi": "Loi de Finance 2023",
      "numero_article": 45,
      "statut": "en_vigueur",
      "langue": "fr",
      "extrait": "..."
    }
  ],
  "jurisprudence": [
    { "case_id": "jp_2021_014", "resume": "...", "reference": "..." }
  ],
  "verification_status": "validated",
  "disclaimer": "Cette réponse ne constitue pas un avis juridique officiel."
}
```

---

## 3bis. Sociétés (`/companies`)

**Implémenté** (2026-09-09) dans `backend/app/api/v1/endpoints/companies.py`.

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| POST | `/companies` | `entreprise`, `admin` | Enregistre une société (nom, matricule fiscal, secteur) et la rattache au compte courant si `entreprise`. |
| GET | `/companies/me` | `entreprise` | Société rattachée au compte courant. |
| GET | `/companies/{company_id}` | `admin` | Détail d'une société. |

**Exemple `POST /companies`**
```json
// Requête
{ "name": "ACME Tunisie SA", "matricule_fiscal": "1234567A", "secteur_activite": "commerce" }

// Réponse
{ "id": "c_1", "name": "ACME Tunisie SA", "matricule_fiscal": "1234567A", "secteur_activite": "commerce", "created_at": "2026-09-09T10:00:00Z" }
```

---

## 3ter. Situation financière et détection d'infraction (`/financial-submissions`)

**Implémenté** (2026-09-09) dans `backend/app/api/v1/endpoints/financial_submissions.py`. C'est le cœur du cas d'usage réel : une société soumet sa situation financière (documents, formulaire structuré, texte libre, ou une combinaison) et reçoit les infractions détectées + la législation applicable, sourcées par le hybrid RAG.

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| POST | `/financial-submissions` | `entreprise` | Crée une soumission (`source_type` + `free_text` et/ou `structured_data`) pour la société du compte courant. |
| POST | `/financial-submissions/{id}/documents` | `entreprise` (propriétaire) | Upload d'un document financier (PDF/Excel/DOCX) attaché à la soumission ; bascule `source_type` à `mixte` si un autre mode était déjà utilisé. |
| GET | `/financial-submissions` | `entreprise` (ses propres soumissions), `admin` (toutes) | Historique des soumissions avec documents et constats. |
| GET | `/financial-submissions/{id}` | `entreprise` (propriétaire), `admin` | Détail d'une soumission (statut, documents, `infraction_findings` + citations). |
| POST | `/financial-submissions/{id}/analyze` | `entreprise` (propriétaire), `admin` | Déclenche l'analyse. |

> ⚠️ **Non implémenté** : `POST /financial-submissions/{id}/analyze` ne fait actuellement que passer le statut à `analyzing` — le câblage vers le pipeline multi-agents (Qualification → recherche légale/jurisprudence → synthèse → vérificateur, section 7 d'ARCHITECTURE.md) pour produire réellement les `infraction_findings` est une étape suivante distincte, pas encore réalisée.

**Exemple `POST /financial-submissions`**
```json
// Requête
{
  "source_type": "formulaire",
  "structured_data": { "chiffre_affaires": 850000, "tva_collectee": 130000, "tva_deduite": 95000 }
}

// Réponse
{
  "id": "fs_1",
  "company_id": "c_1",
  "source_type": "formulaire",
  "status": "pending",
  "structured_data": { "chiffre_affaires": 850000, "tva_collectee": 130000, "tva_deduite": 95000 },
  "documents": [],
  "findings": [],
  "created_at": "2026-09-09T10:05:00Z"
}
```

---

## 4. Documents et ingestion (`/documents`, `/ingestion`) — admin

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| POST | `/documents/upload` | `admin` | Upload d'un ou plusieurs documents bruts (PDF/DOCX/image) vers le stockage brut (MinIO). |
| GET | `/documents` | `admin` | Liste des documents avec statut (`uploaded`, `ocr_en_cours`, `indexe`, `erreur`). |
| GET | `/documents/{document_id}` | `admin` | Détail d'un document (métadonnées, historique de traitement). |
| DELETE | `/documents/{document_id}` | `admin` | Supprime un document et ses index associés (Qdrant/Neo4j). |
| POST | `/documents/{document_id}/reprocess` | `admin` | Relance le pipeline d'ingestion sur un document spécifique. |
| GET | `/documents/{document_id}/status` | `admin` | Statut détaillé étape par étape (OCR, parsing, indexation). |
| POST | `/ingestion/run` | `admin` | Déclenche un job d'ingestion batch sur un dossier/lot de documents. |
| GET | `/ingestion/jobs` | `admin` | Liste des jobs d'ingestion (en cours/terminés/échoués). |
| GET | `/ingestion/jobs/{job_id}` | `admin` | Détail d'un job (progression, erreurs, documents traités). |

---

## 5. Consultation du corpus légal (`/articles`)

Accès direct au corpus indexé, indépendamment du raisonnement multi-agents (utile pour recherche manuelle par un avocat/juge).

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| GET | `/articles` | `avocat`, `juge`, `admin` | Recherche/liste d'articles avec filtres (`annee`, `statut`, `categorie_infraction`, `langue`, texte libre). |
| GET | `/articles/{article_id}` | `avocat`, `juge`, `admin` | Détail complet d'un article (texte, métadonnées, version liée AR/FR). |
| GET | `/articles/{article_id}/related` | `avocat`, `juge`, `admin` | Articles liés via le graphe (amendements, abrogations, citations). |
| GET | `/articles/{article_id}/history` | `avocat`, `juge`, `admin` | Historique des modifications légales de l'article. |

---

## 6. Jurisprudence (`/jurisprudence`)

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| GET | `/jurisprudence` | `avocat`, `juge`, `admin` | Recherche/liste d'affaires (filtres : catégorie, année, juridiction). |
| GET | `/jurisprudence/{case_id}` | `avocat`, `juge`, `admin` | Détail d'une affaire (résumé, articles cités, décision). |
| GET | `/jurisprudence/{case_id}/similar` | `avocat`, `juge`, `admin` | Affaires similaires (recherche hybride). |
| POST | `/jurisprudence` | `admin` | Ajout manuel d'une décision (hors pipeline d'ingestion automatique). |

---

## 7. Taxonomie des infractions (`/taxonomy`)

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| GET | `/taxonomy/categories` | authentifié | Liste des catégories d'infractions financières. |
| POST | `/taxonomy/categories` | `admin` | Ajoute une nouvelle catégorie. |
| PATCH | `/taxonomy/categories/{category_id}` | `admin` | Modifie une catégorie (libellé, description). |
| DELETE | `/taxonomy/categories/{category_id}` | `admin` | Supprime une catégorie (si non utilisée). |

---

## 8. Évaluation (`/eval`) — admin

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| GET | `/eval/test-cases` | `admin` | Liste des cas de test validés par un juriste. |
| POST | `/eval/test-cases` | `admin` | Ajoute un nouveau cas de test. |
| POST | `/eval/run` | `admin` | Exécute le jeu de test complet contre le pipeline et calcule les métriques. |
| GET | `/eval/results` | `admin` | Historique des exécutions d'évaluation. |
| GET | `/eval/results/{run_id}` | `admin` | Détail des métriques d'une exécution (précision de citation, taux d'hallucination, recall@k). |

---

## 9. Journal d'audit (`/audit-logs`) — admin, traçabilité judiciaire

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| GET | `/audit-logs` | `admin` | Liste paginée des requêtes/réponses (filtres : utilisateur, période, rôle). |
| GET | `/audit-logs/{log_id}` | `admin` | Détail complet d'une entrée d'audit (immutabilité garantie). |

---

## 10. Santé du système (`/health`)

| Méthode | Endpoint | Rôles | Description |
|---|---|---|---|
| GET | `/health` | public | Statut général de l'API (liveness). |
| GET | `/health/dependencies` | `admin` | Vérifie la connectivité à PostgreSQL, Qdrant, Neo4j, vLLM, MinIO. |

---

## 11. Récapitulatif par rôle

| Rôle | Endpoints accessibles |
|---|---|
| **entreprise** (rôle principal) | `/auth/*` (self), `/users/me`, `/companies` (création + `/me`), `/financial-submissions/*` (ses propres soumissions), `/taxonomy/categories` |
| **citoyen** | `/auth/*` (self), `/users/me`, `/query`, `/query/history`, `/query/{id}`, `/query/{id}/feedback`, `/taxonomy/categories` |
| **avocat** | tout ce qui précède (profil citoyen) + `/articles/*`, `/jurisprudence/*` |
| **juge** | mêmes accès qu'avocat (le format de réponse `/query` diffère, pas les permissions d'accès) |
| **admin** | accès complet à tous les endpoints, y compris `/documents/*`, `/ingestion/*`, `/eval/*`, `/audit-logs/*`, `/health/dependencies`, gestion `/users`/`/taxonomy`/`/companies`/`/financial-submissions` (toutes sociétés) |

---

## 12. Codes d'erreur standards

| Code | Signification |
|---|---|
| 400 | Requête invalide (validation Pydantic échouée) |
| 401 | Non authentifié / token invalide ou expiré |
| 403 | Rôle insuffisant pour l'action demandée |
| 404 | Ressource introuvable (article, document, requête, utilisateur) |
| 409 | Conflit (ex : email déjà utilisé) |
| 422 | Erreur de traitement métier (ex : document illisible après OCR) |
| 500 | Erreur serveur interne |
| 503 | Dépendance indisponible (Qdrant/Neo4j/vLLM injoignable) |
