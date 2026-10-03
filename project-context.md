# Projet: Système Agentic Hybrid RAG - Loi de finance tunisienne

## Objectif
Système multi-agents destiné à une **société/entreprise** : celle-ci fournit toutes les informations
sur sa situation financière actuelle (comptabilité, déclarations fiscales, opérations, etc.), et le
chatbot analyse ces informations à la lumière de sa base de connaissances RAG (corpus fiscal tunisien :
codes permanents, lois de finance, notes communes DGI) pour identifier les **manquements/sanctions
fiscales** dans lesquels la société pourrait être impliquée et la **législation applicable** à sa
situation.

> Précision (2026-09-09) : ceci corrige/remplace le cadrage précédent qui décrivait un assistant de
> questions-réponses juridiques pour avocats/juges/citoyens. Le cas d'usage réel est un outil de
> détection de conformité/infraction pour une société, pas un Q&A juridique généraliste. Voir
> `project_goal_clarification` en mémoire pour le contexte complet.

> Resserrement de périmètre (2026-10-02) : après inventaire du corpus réel (1189 documents dans
> `data/raw/pdfs/`, séparés en `fr/`/`ar/`), le périmètre est resserré au **droit fiscal** — voir
> `QUESTIONS_SITUATION_FINANCIERE.md` pour le détail des règles extraites (CDPF, Code IRPP/IS) et
> `ARCHITECTURE.md §1/§6` pour la taxonomie mise à jour. Aucune jurisprudence n'est disponible dans le
> corpus collecté ; les catégories douane/blanchiment/abus de biens sociaux/change/corruption n'ont
> aucun document source et sont hors périmètre tant qu'elles ne sont pas collectées.

## Entrée des données de la société
La société peut fournir sa situation financière de trois façons combinées :
- **Documents à uploader** (PDF/Excel/DOCX : bilans, déclarations fiscales, etc.) — traités par le
  pipeline d'ingestion, comme les lois/jurisprudence.
- **Formulaire structuré** (champs précis : chiffre d'affaires, TVA collectée/déduite, etc.).
- **Description en langage libre** dans le chat, comme le fait déjà l'agent Qualification actuel.

## Périmètre
- Droit fiscal tunisien (IRPP, IS, TVA, fiscalité locale, droits d'enregistrement, CDPF) — pas le code
  pénal général, pas la douane, pas le blanchiment (aucun corpus source disponible actuellement)
- Utilisateur cible principal : la société/entreprise soumettant sa situation financière
  (avocats/juges/citoyens restent des profils possibles mais secondaires à préciser)

## Données
- Corpus mixte: documents texte propre + PDF scannés (nécessite OCR) — confirmé empiriquement
  (ex: certaines éditions scannées du Code IRPP/IS n'ont produit aucun texte avec le pipeline standard)
- Bilingue: arabe et français — 1189 PDF au total, séparés le 2026-10-02 en
  `data/raw/pdfs/fr/` (708) et `data/raw/pdfs/ar/` (481)
- Risque identifié: OCR arabe fragile avec outils standards, nécessite solution dédiée + relecture humaine
- Décision structurelle recommandée: lier les versions AR/FR d'un même article par un ID commun
- Composition réelle du corpus (voir `QUESTIONS_SITUATION_FINANCIERE.md` §1) : notes communes DGI
  (~85% des fichiers), codes fiscaux permanents (CDPF, IRPP/IS, TVA, fiscalité locale, droits
  d'enregistrement), lois de finance annuelles, conventions fiscales bilatérales — aucune jurisprudence

## Statut d'avancement
- Phase actuelle: cadrage / préparation des données (PAS ENCORE l'architecture technique)
- Étapes recommandées définies (voir conversation): audit corpus, pipeline OCR bilingue,
  structuration par article + métadonnées, taxonomie des infractions financières,
  schéma de réponse adaptable par profil utilisateur, jeu de test de 10-20 cas validés par juriste,
  POC minimal sur un seul cas d'usage avant généralisation.
- Architecture technique (ingestion, indexation hybride, orchestration multi-agents) à faire APRÈS
  validation de ces fondations.

## Préférence de communication
- Utilisateur communique en français (avec quelques fautes/tournures), répondre en français.
