# Projet: Système Agentic Hybrid RAG - Loi de finance tunisienne

## Objectif
Système multi-agents pour aider avocats, juges et citoyens à comprendre les peines/sanctions
liées aux infractions de la loi de finance tunisienne, en s'appuyant sur des documents
juridiques anciens collectés (lois + jurisprudence).

## Périmètre
- Strictement la loi de finance tunisienne (pas le code pénal général, sauf lien direct)
- Utilisateurs cibles: avocats, juges, citoyens (tous, à terme) - POC recommandé sur un seul profil d'abord

## Données
- Corpus mixte: documents texte propre + PDF scannés (nécessite OCR)
- Bilingue: arabe et français
- Risque identifié: OCR arabe fragile avec outils standards, nécessite solution dédiée + relecture humaine
- Décision structurelle recommandée: lier les versions AR/FR d'un même article par un ID commun

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
