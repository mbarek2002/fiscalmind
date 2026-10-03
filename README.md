# Agentic Hybrid RAG — Loi de Finance Tunisienne

Système multi-agents (RAG hybride) destiné à une **société/entreprise** : celle-ci fournit sa situation financière actuelle (documents à uploader, formulaire structuré, ou description libre — les trois modes sont combinables), et le système l'analyse à la lumière du corpus fiscal tunisien collecté (codes permanents, lois de finance, notes communes DGI) pour identifier les **manquements/sanctions fiscales** et la **législation applicable** à sa situation.

> **Périmètre resserré (2026-10-02)** : voir [QUESTIONS_SITUATION_FINANCIERE.md](./QUESTIONS_SITUATION_FINANCIERE.md) pour le détail des questions couvertes par les données réellement collectées. Le corpus actuel est 100% fiscal et ne contient aucune jurisprudence — voir [ARCHITECTURE.md §1](./ARCHITECTURE.md#1-objectif-du-projet).

> ⚠️ Ce système est une aide à la compréhension juridique et à la détection de conformité. Il ne remplace en aucun cas un avis juridique officiel.

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) — architecture complète : pipeline d'ingestion, recherche hybride (dense + sparse + graphe), agents multi-agents (LangGraph), stack technique, sécurité, plan de mise en œuvre.
- [STRUCTURE.md](./STRUCTURE.md) — arborescence détaillée du projet, rôle de chaque fichier, dépendances, variables d'environnement, services Docker.
- [DATA_SCHEMA.md](./DATA_SCHEMA.md) — schéma détaillé PostgreSQL (DDL), Neo4j (nœuds/relations/contraintes) et Qdrant (collections/payload).
- [ENDPOINTS.md](./ENDPOINTS.md) — spécification complète des endpoints API REST (auth, query, documents/ingestion, articles, jurisprudence, taxonomie, évaluation, audit).

## Périmètre

- **Domaine** : droit fiscal tunisien (IRPP, IS, TVA, fiscalité locale, droits d'enregistrement — contrôle, procédures, infractions et sanctions du CDPF). Voir [ARCHITECTURE.md — section 1.1](./ARCHITECTURE.md#11-clarification--composition-du-domaine-finance) pour la clarification de la composition du domaine "finance" et l'historique du resserrement de périmètre vers le fiscal.
- **Langues** : arabe et français (corpus bilingue aligné article par article)
- **Utilisateur principal** : la société/entreprise soumettant sa situation financière (avocats, juges, citoyens restent des profils secondaires possibles, à préciser — même moteur, sortie adaptée au profil)
- **Hybrid RAG** : recherche dense (BGE-M3) + sparse (BM25) + graphe de connaissances (Neo4j)
- **LLM** : self-hosted (Qwen2.5-14B-Instruct-AWQ via vLLM, GPU 24 Go) pour la confidentialité des données juridiques

## Stack technique

| Composant | Choix |
|---|---|
| Backend | FastAPI (Python) |
| Orchestration agents | LangGraph |
| Embeddings / reranking | BGE-M3 / BGE-reranker-v2-m3 (self-hosted) |
| Base vectorielle | Qdrant |
| Base graphe | Neo4j |
| Base relationnelle | PostgreSQL |
| LLM | Qwen2.5-14B-Instruct-AWQ via vLLM (self-hosted, GPU 24 Go) |
| Frontend | Next.js + TypeScript |
| Observabilité | Langfuse |
| Conteneurisation | Docker Compose |

Détails complets et justifications dans [ARCHITECTURE.md](./ARCHITECTURE.md).

## Structure du projet

Voir l'arborescence complète et le rôle de chaque fichier dans [STRUCTURE.md](./STRUCTURE.md). Résumé :

```
low/
├── backend/      # API FastAPI, agents LangGraph, pipeline d'ingestion
├── frontend/     # Interface Next.js
├── data/         # Documents bruts, traités, jeu de test
├── infra/        # Configurations Qdrant, Neo4j, vLLM, Langfuse, MinIO
└── docker-compose.yml
```

## Prérequis

- Docker et Docker Compose
- GPU disponible (pour l'inférence LLM self-hosted via vLLM et les modèles d'embeddings)
- Python 3.11+ (développement backend hors conteneur)
- Node.js 20+ (développement frontend hors conteneur)

## Installation et démarrage

1. Copier le fichier d'environnement et renseigner les valeurs :
   ```bash
   cp .env.example .env
   ```
2. Lancer l'ensemble des services :
   ```bash
   docker compose up --build
   ```
3. Accéder aux interfaces :
   - Frontend : http://localhost:3000
   - API backend : http://localhost:8000
   - Neo4j Browser : http://localhost:7474
   - Langfuse : http://localhost:3001

## Pipeline d'indexation

Pour ingérer de nouveaux documents (lois de finance, jurisprudence) :
```bash
docker compose exec backend python scripts/run_ingestion.py --source data/raw
```

## Évaluation

Exécuter le jeu de test de référence (cas validés par un juriste) contre le pipeline complet :
```bash
docker compose exec backend python scripts/evaluate.py
```

## État d'avancement

Projet en phase de cadrage architecture / préparation des fondations de données (voir [ARCHITECTURE.md](./ARCHITECTURE.md#12-plan-de-mise-en-œuvre-phases) — Phase 0 en cours). Le scaffolding du code n'est pas encore réalisé.

## Sécurité et confidentialité

- LLM et embeddings self-hosted : aucune donnée juridique envoyée à un tiers externe.
- Authentification JWT et contrôle d'accès par rôle (RBAC).
- Journalisation d'audit immuable de toutes les requêtes.

Détails dans [ARCHITECTURE.md — section Sécurité](./ARCHITECTURE.md#10-sécurité).
