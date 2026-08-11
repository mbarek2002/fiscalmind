# Schéma de données détaillé — PostgreSQL, Neo4j, Qdrant

Complète [ARCHITECTURE.md](./ARCHITECTURE.md) (sections 4, 5, 9) avec le schéma exact des trois bases de données.

---

## 1. PostgreSQL — métadonnées, utilisateurs, audit (source de vérité)

### 1.1 `users`
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('citoyen', 'avocat', 'juge', 'admin')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    preferred_lang  VARCHAR(5) NOT NULL DEFAULT 'fr' CHECK (preferred_lang IN ('fr', 'ar')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_role ON users(role);
```

### 1.2 `documents_metadata`
Table de vérité pour le statut légal — indépendante du vector store (Qdrant peut être réindexé sans perte d'information).
```sql
CREATE TABLE documents_metadata (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type         VARCHAR(20) NOT NULL CHECK (source_type IN ('loi', 'jurisprudence')),
    titre               VARCHAR(500) NOT NULL,
    annee_loi           INT,
    numero_article      INT,
    langue              VARCHAR(5) NOT NULL CHECK (langue IN ('fr', 'ar')),
    id_article_lie      UUID,                       -- pointe vers la version dans l'autre langue
    statut              VARCHAR(20) NOT NULL DEFAULT 'en_vigueur'
                        CHECK (statut IN ('en_vigueur', 'modifie', 'abroge')),
    date_entree_vigueur DATE,
    date_abrogation     DATE,
    categorie_infraction TEXT[],                     -- tags taxonomie
    ingestion_status    VARCHAR(20) NOT NULL DEFAULT 'uploaded'
                        CHECK (ingestion_status IN ('uploaded','ocr_en_cours','normalise','parse','indexe','erreur')),
    storage_path        VARCHAR(1000) NOT NULL,       -- chemin MinIO du document brut
    anonymized          BOOLEAN NOT NULL DEFAULT FALSE, -- true requis si source_type='jurisprudence'
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_docs_statut ON documents_metadata(statut);
CREATE INDEX idx_docs_annee ON documents_metadata(annee_loi);
CREATE INDEX idx_docs_categorie ON documents_metadata USING GIN (categorie_infraction);
CREATE INDEX idx_docs_source_type ON documents_metadata(source_type);
```

### 1.3 `taxonomy_categories`
```sql
CREATE TABLE taxonomy_categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(50) NOT NULL UNIQUE,   -- ex: 'fraude_fiscale_tva'
    libelle_fr  VARCHAR(255) NOT NULL,
    libelle_ar  VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 1.4 `ingestion_jobs`
```sql
CREATE TABLE ingestion_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','completed','failed')),
    total_documents INT NOT NULL DEFAULT 0,
    processed_count INT NOT NULL DEFAULT 0,
    error_count     INT NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id)
);
```

### 1.5 `audit_logs` (immuable — traçabilité judiciaire)
```sql
CREATE TABLE audit_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id),
    user_role           VARCHAR(20) NOT NULL,
    query_id            UUID NOT NULL,
    question            TEXT NOT NULL,
    final_answer        TEXT NOT NULL,
    citations           JSONB NOT NULL DEFAULT '[]',
    verification_status VARCHAR(20) NOT NULL,
    retry_count         INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Aucune contrainte UPDATE/DELETE applicative : table append-only.
-- Recommandé : REVOKE UPDATE, DELETE ON audit_logs FROM app_role; (trigger de protection en Phase 5)
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
```

### 1.6 `eval_test_cases` et `eval_runs`
```sql
CREATE TABLE eval_test_cases (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facts                   TEXT NOT NULL,
    expected_category       TEXT[] NOT NULL,
    expected_article_ids    UUID[] NOT NULL,
    expected_answer_summary TEXT NOT NULL,
    validated_by            VARCHAR(255) NOT NULL,   -- nom du juriste validateur
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE eval_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    precision_citation  NUMERIC(5,2),
    taux_hallucination  NUMERIC(5,2),
    recall_at_k         NUMERIC(5,2),
    taux_rejet_verifier NUMERIC(5,2),
    details             JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 1.7 Table de mapping d'anonymisation (accès restreint `admin`)
```sql
CREATE TABLE anonymization_mapping (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents_metadata(id),
    token           VARCHAR(50) NOT NULL,        -- ex: 'PERSONNE_1'
    real_value_enc  BYTEA NOT NULL,              -- valeur réelle chiffrée (AES-GCM applicatif)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Accès restreint via RBAC applicatif : uniquement rôle admin + justification légale loggée.
```

### 1.8 Diagramme entité-relation (vue d'ensemble)

```mermaid
erDiagram
    USERS ||--o{ AUDIT_LOGS : "génère"
    USERS ||--o{ INGESTION_JOBS : "déclenche"
    DOCUMENTS_METADATA ||--o{ ANONYMIZATION_MAPPING : "anonymise"
    DOCUMENTS_METADATA }o--o{ TAXONOMY_CATEGORIES : "catégorise (tag)"
    DOCUMENTS_METADATA ||--o| DOCUMENTS_METADATA : "version liée AR/FR"

    USERS {
        uuid id PK
        string email
        string role
        boolean is_active
    }
    DOCUMENTS_METADATA {
        uuid id PK
        string source_type
        int annee_loi
        int numero_article
        string langue
        uuid id_article_lie FK
        string statut
        boolean anonymized
    }
    TAXONOMY_CATEGORIES {
        uuid id PK
        string code
        string libelle_fr
        string libelle_ar
    }
    INGESTION_JOBS {
        uuid id PK
        string status
        int total_documents
        uuid created_by FK
    }
    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        uuid query_id
        string verification_status
    }
    EVAL_TEST_CASES {
        uuid id PK
        string facts
        string validated_by
    }
    EVAL_RUNS {
        uuid id PK
        decimal precision_citation
        decimal taux_hallucination
    }
    ANONYMIZATION_MAPPING {
        uuid id PK
        uuid document_id FK
        string token
    }
```

> Note : la relation `DOCUMENTS_METADATA }o--o{ TAXONOMY_CATEGORIES` est un lien logique (via le tableau `categorie_infraction`), pas une clé étrangère stricte — représentée ici pour la lisibilité du modèle.

---

## 2. Neo4j — graphe légal

### 2.1 Labels de nœuds et propriétés

| Label | Propriétés clés |
|---|---|
| `Article` | `id` (UUID, unique), `numero`, `annee_loi`, `langue`, `statut`, `id_article_lie` |
| `Loi` | `id`, `nom` (ex: "Loi de Finance 2023"), `annee`, `date_publication` |
| `Jurisprudence` | `id`, `reference`, `date_decision`, `juridiction`, `anonymized` (bool) |
| `Categorie` | `id`, `code`, `libelle_fr`, `libelle_ar` |

### 2.2 Contraintes et index
```cypher
CREATE CONSTRAINT article_id_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT loi_id_unique IF NOT EXISTS FOR (l:Loi) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT jurisprudence_id_unique IF NOT EXISTS FOR (j:Jurisprudence) REQUIRE j.id IS UNIQUE;
CREATE CONSTRAINT categorie_code_unique IF NOT EXISTS FOR (c:Categorie) REQUIRE c.code IS UNIQUE;

CREATE INDEX article_statut_idx IF NOT EXISTS FOR (a:Article) ON (a.statut);
CREATE INDEX article_annee_idx IF NOT EXISTS FOR (a:Article) ON (a.annee_loi);
```

### 2.3 Types de relations

| Relation | Sens | Propriétés |
|---|---|---|
| `(:Article)-[:APPARTIENT_A]->(:Loi)` | rattachement | — |
| `(:Article)-[:MODIFIE]->(:Article)` | amendement | `date_modification` |
| `(:Article)-[:ABROGE]->(:Article)` | abrogation | `date_abrogation` |
| `(:Article)-[:APPARTIENT_CATEGORIE]->(:Categorie)` | classification | — |
| `(:Jurisprudence)-[:CITE]->(:Article)` | citation légale dans une décision | `contexte` |
| `(:Jurisprudence)-[:SIMILAIRE_A]->(:Jurisprudence)` | similarité calculée a posteriori | `score` |
| `(:Article)-[:VERSION_LINGUISTIQUE]->(:Article)` | lien AR ↔ FR du même article | — |

### 2.4 Exemple de graphe instancié

```mermaid
flowchart LR
    L[":Loi<br/>Loi de Finance 2023"]
    A1[":Article<br/>Article 45 FR"]
    A1AR[":Article<br/>Article 45 AR"]
    A2[":Article<br/>Article 12 loi antérieure"]
    C[":Categorie<br/>fraude_fiscale_tva"]
    J1[":Jurisprudence<br/>Affaire 2021-014"]
    J2[":Jurisprudence<br/>Affaire 2022-031"]

    A1 -->|APPARTIENT_A| L
    A1 -->|APPARTIENT_CATEGORIE| C
    A1 -->|VERSION_LINGUISTIQUE| A1AR
    A1 -->|MODIFIE| A2
    J1 -->|CITE| A1
    J1 -->|SIMILAIRE_A| J2
```

### 2.5 Exemple de requête (contexte multi-sauts pour l'agent de recherche légale)
```cypher
MATCH (a:Article {id: $article_id})
OPTIONAL MATCH (a)-[:MODIFIE|ABROGE]-(lie:Article)
OPTIONAL MATCH (j:Jurisprudence)-[:CITE]->(a)
RETURN a, collect(DISTINCT lie) AS articles_lies, collect(DISTINCT j) AS jurisprudence_citante;
```

---

## 3. Qdrant — collections vectorielles

### 3.1 Collections
| Collection | Contenu | Dimension vecteur dense | Distance |
|---|---|---|---|
| `loi_finance` | Chunks d'articles de la loi de finance | 1024 (BGE-M3) | Cosine |
| `jurisprudence` | Résumés/chunks de décisions (anonymisées) | 1024 (BGE-M3) | Cosine |

Chaque collection est configurée en **mode hybride** : vecteur dense nommé `dense` + vecteur sparse nommé `sparse` (BGE-M3 sparse output), permettant une requête combinée native Qdrant (`query_points` avec fusion RRF).

### 3.2 Configuration (exemple `qdrant-client`)
```python
from qdrant_client.models import VectorParams, Distance, SparseVectorParams

client.create_collection(
    collection_name="loi_finance",
    vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
    sparse_vectors_config={"sparse": SparseVectorParams()},
)
```

### 3.3 Schéma du payload (par point / chunk)
```json
{
  "id_chunk": "lf2023_art45_fr",
  "id_article_lie": "lf2023_art45",
  "document_id": "uuid-postgres-documents_metadata",
  "annee_loi": 2023,
  "numero_article": 45,
  "langue": "fr",
  "statut": "en_vigueur",
  "categorie_infraction": ["fraude_fiscale", "tva"],
  "texte": "..."
}
```

### 3.4 Index de payload (filtrage rapide)
```python
client.create_payload_index("loi_finance", field_name="statut", field_schema="keyword")
client.create_payload_index("loi_finance", field_name="categorie_infraction", field_schema="keyword")
client.create_payload_index("loi_finance", field_name="langue", field_schema="keyword")
client.create_payload_index("loi_finance", field_name="annee_loi", field_schema="integer")
```

---

## 4. Cohérence entre les trois bases

- **`id_chunk` / `document_id`** relie chaque point Qdrant à une ligne `documents_metadata` (Postgres) — Postgres reste la source de vérité pour le `statut` légal (en cas de désaccord, Postgres prime, une tâche de synchronisation périodique met à jour le payload Qdrant).
- **`id` Neo4j `Article`** correspond au même UUID que `documents_metadata.id` — permet de faire des jointures applicatives simples entre le graphe et les métadonnées relationnelles.
- **Mise à jour du statut d'un article** (ex : abrogation par une nouvelle loi de finance) : une seule opération transactionnelle applicative met à jour Postgres, le payload Qdrant correspondant, et crée la relation `ABROGE` dans Neo4j.
