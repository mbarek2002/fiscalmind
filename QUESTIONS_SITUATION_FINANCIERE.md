# Situation financière d'une société → décisions de l'État possibles

Ce document synthétise, à partir du corpus français déjà extrait (`data/processed/opendataloader_sample/`, issu de `data/raw/pdfs/fr/`), **ce que le système FiscalMind peut concrètement déduire** de la situation financière d'une société, et **quelles questions il est capable de répondre**. Les règles citées ci-dessous sont extraites telles quelles des codes fiscaux tunisiens (références d'articles vérifiées), pas inventées — elles servent de base de référence pour l'agent Qualification/Synthèse.

> ⚠️ Ceci n'est pas un avis juridique. C'est un extrait de référence pour guider le développement du moteur de règles/RAG.

---

## 1. Sources utilisées pour cette analyse

| Document | Ce qu'il contient | Pertinence |
|---|---|---|
| **CDPF** (`cdpf-2025.pdf`, Code des Droits et Procédures Fiscaux) | Contrôle fiscal, taxation d'office, **sanctions fiscales** (Titre III), recours | C'est **le** code qui définit les décisions que l'État peut prendre contre une société (amendes, pénalités, taxation d'office) |
| **Code de l'IRPP/IS** (`Code-de-limpot-sur-le-Revenu...2023.pdf`) | Régimes d'imposition, seuils de chiffre d'affaires, barèmes | Détermine le régime fiscal applicable selon la situation de l'entreprise |
| Code de la TVA, Code de la Fiscalité Locale, Code des Droits d'Enregistrement et de Timbre | Règles spécifiques par impôt | Complètent la détection d'infraction par type de taxe |

---

## 2. Décisions de l'État possibles, par fait financier constaté

### 2.1 Retard de paiement de l'impôt (Art. 81, 82 CDPF)

| Fait constaté | Décision / sanction |
|---|---|
| Retard de paiement **déclaré spontanément** (sans contrôle fiscal) | Pénalité de retard **1,25% par mois** de retard ; **+3% fixe** si le retard dépasse 60 jours. Plafond : la somme ne peut excéder le montant de l'impôt principal exigible. |
| Retard **constaté suite à un contrôle fiscal** | Pénalité **2,25% par mois** + pénalité fixe **10%** — portée à **20%** pour la TVA/taxes sur le CA non payées, ou si **minoration du chiffre d'affaires ≥ 30%** ou manœuvres de fraude fiscale. |
| Reconnaissance de dette + paiement sous 30 jours, avant notification de taxation d'office | Taux réduits : pénalité de retard ramenée à 1,25%, pénalité fixe réduite de 50%. |

**Question que le système peut répondre** : *« Si l'entreprise a un retard de paiement de TVA de 90 jours détecté lors d'un contrôle, et que le chiffre d'affaires déclaré est inférieur de 35% au chiffre d'affaires réel, quelle pénalité risque-t-elle ? »* → Art. 82 : pénalité 2,25%/mois + 20% (minoration ≥30%).

### 2.2 Défaut/insuffisance de retenue à la source (Art. 83 CDPF)

- Pénalité = **montant non retenu** (ou insuffisamment retenu).
- **Doublée en cas de récidive** dans les 2 ans.

**Question répondable** : *« L'entreprise n'a pas effectué de retenue à la source sur un paiement, et c'est la 2e fois en 18 mois — quelle sanction ? »* → pénalité doublée (récidive < 2 ans).

### 2.3 Paiement en espèces de montants élevés (Art. 83 ter CDPF)

- Paiement en espèces **≥ 5 000 dinars** (achats d'actifs, services, produits) → amende **20% du montant**, minimum **2 000 dinars**.

**Question répondable** : *« L'entreprise a réglé 8 000 dinars en espèces pour un achat — quel est le risque ? »* → amende de 1 600 dinars, mais minimum légal 2 000 dinars appliqué → **2 000 dinars**.

### 2.4 Transferts de bénéfices / prix de transfert (Art. 84 bis CDPF, renvoi Art. 112)

- Transfert de revenus/bénéfices sans respecter les conditions de l'art. 112 :
  - **20%** du montant transféré si ces revenus étaient imposables en Tunisie,
  - **1%** si non imposables en Tunisie.

**Question répondable** : *« Une société transfère des bénéfices à une filiale étrangère sans documentation de prix de transfert conforme — quelle amende ? »* → 20% (si bénéfices normalement imposables en Tunisie).

### 2.5 Défaut de paiement du droit de timbre (Art. 84 CDPF)

- Pénalité = **50%** du droit non acquitté, en sus du droit principal.

### 2.6 Taxation d'office (Art. 47-51 bis CDPF)

Déclenchée quand :
- désaccord entre l'administration et le contribuable sur les résultats d'une vérification fiscale, **ou**
- le contribuable **ne répond pas** à la notification des résultats dans les délais, **ou**
- **défaut de dépôt des déclarations fiscales** dans les 30 jours suivant une mise en demeure.

Montant minimum d'impôt non susceptible de restitution (Art. 48) :
- **200 dinars** pour les personnes morales,
- **100 dinars** pour les personnes physiques au régime réel (ou forfaitaire pour bénéfices non commerciaux),
- **50 dinars** régime forfaitaire (bénéfices industriels/commerciaux),
- **25 dinars** autres cas.

**Question répondable** : *« L'entreprise (personne morale) n'a pas déposé sa déclaration fiscale malgré une mise en demeure il y a 35 jours — que risque-t-elle ? »* → taxation d'office, minimum 200 dinars d'impôt non restituable, sur la base de présomptions ou de la dernière déclaration déposée.

---

## 3. Déterminer le régime fiscal applicable (préalable à toute analyse d'infraction)

Avant de qualifier une infraction, il faut situer l'entreprise par rapport à son régime :

| Situation | Régime |
|---|---|
| Entreprise individuelle, bénéfices industriels/commerciaux, établissement unique, **CA annuel ≤ 100 000 dinars** | Régime forfaitaire (Art. 44 bis Code IRPP/IS) |
| CA annuel ≤ 150 000 dinars, option pour le régime réel | Comptabilité simplifiée possible (Art. 44 III ter) |
| Au-delà des seuils, ou non-respect des conditions du régime forfaitaire (hors seuil de CA) | Régime réel — retrait du régime forfaitaire **par décision motivée** du directeur général des impôts ou du chef de centre régional de contrôle (Art. 44 sexies) |

**Question répondable** : *« Une entreprise individuelle déclare un CA de 120 000 dinars alors qu'elle est au régime forfaitaire (plafond 100 000) — quelle conséquence ? »* → dépassement du seuil, bascule vers le régime réel (le retrait du forfaitaire pour ce motif spécifique n'exige pas de décision motivée, contrairement aux autres conditions de l'Art. 44 bis).

---

## 4. Catalogue récapitulatif — types de questions que le système peut traiter

À partir d'une situation financière soumise (documents, formulaire ou texte), le système devrait pouvoir répondre à des questions du type :

1. **Quel régime fiscal s'applique** à cette société compte tenu de son chiffre d'affaires et de son activité ?
2. **Y a-t-il un retard de paiement** d'un impôt, et si oui, quelle pénalité (taux, plafond) s'applique selon qu'il a été déclaré spontanément ou détecté par contrôle ?
3. **Le chiffre d'affaires déclaré est-il cohérent** avec les éléments fournis (risque de minoration ≥30% déclenchant une pénalité aggravée) ?
4. **Les retenues à la source ont-elles été correctement effectuées** ? Est-ce un cas de récidive ?
5. **Des paiements en espèces dépassent-ils le seuil de 5 000 dinars** nécessitant une amende ?
6. **Y a-t-il eu un transfert de bénéfices** vers une entité liée sans respect des règles de prix de transfert ?
7. **La société a-t-elle déposé ses déclarations fiscales** dans les délais ? Risque de taxation d'office ?
8. **Quel est le montant minimum d'impôt** exigible en cas de taxation d'office, selon le statut (personne morale/physique, régime) ?
9. **Le droit de timbre a-t-il été acquitté** correctement ?

Chaque réponse doit être **sourcée** (numéro d'article + code + année de la loi de finance qui l'a modifié, car ces articles sont fréquemment amendés — voir les nombreuses notes de bas de page "modifié par l'article X de la loi de finances pour l'année Y" dans le CDPF) et accompagnée du disclaimer habituel.

---

## 5. Limite de cette analyse

Ce document est basé sur un **échantillon** déjà extrait (une vingtaine de codes/lois sur les 708 fichiers français du corpus), centré sur le CDPF et le Code IRPP/IS. Il ne couvre pas encore :
- les ~594 **Notes communes** (interprétations DGI cas par cas) qui affinent chacune de ces règles,
- le Code de la TVA et le Code de la Fiscalité Locale en détail (seulement repérés, pas encore dépouillés article par article),
- les Lois de Finance annuelles qui modifient ces taux chaque année (le CDPF ci-dessus montre que les taux de pénalité ont changé presque chaque année entre 2006 et 2024 — **la date des faits est donc critique** pour appliquer le bon taux, cf. principe de non-rétroactivité déjà documenté dans ARCHITECTURE.md §5.1).
