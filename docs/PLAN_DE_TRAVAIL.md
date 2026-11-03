# Plan de travail du binôme

Massamba et Sine. Ce plan dit **ce qu'on fait ensemble**, ce qu'on fait **chacun de son côté**, et comment on reste cohérents. Le détail route par route et règle par règle est dans [`SUIVI.md`](SUIVI.md).

## 0. Point de départ : ce qui existe déjà

| Déjà fait | Où |
|---|---|
| Les 8 modèles SQLAlchemy et leurs relations | `app/models/` |
| Configuration `.env`, session, hachage Argon2, JWT, contrôle des rôles | `app/core/` |
| Erreurs métier (`Conflit`, `DonneesInvalides`...) renvoyées en `{"detail": ...}` | `app/core/errors.py`, handler dans `app/main.py` |
| Routes 1, 2 (`/auth/login`, `/auth/me`) et 44 (`/health`) | `app/routers/auth.py`, `health.py` |
| Fonctions pures testées : RG1, RG5, RG7, RG8, RG11, RG13 | `app/services/` |
| Script de seed (admin + catalogue de l'annexe B) | `app/seed.py` |
| Alembic configuré, Dockerfile, docker-compose, `.env.example` | racine |
| 31 tests qui passent | `tests/` |
| Un fichier par routeur, vide, avec l'en-tête « routes, responsable, règles » | `app/routers/` |

**Pas encore fait** : aucune migration Alembic (donc `docker compose up` ne crée pas les tables), aucun schéma Pydantic (hors `auth`), 41 routes sur 44.

## 1. Étape 0, ensemble, une seule session

Faites-la côte à côte (ou en visio) : tout le reste en dépend.

- [ ] **Environnement** : `cp .env.example .env`, remplir les valeurs, créer un venv, `pip install -r requirements.txt`, lancer `pytest` (31 verts chez les deux).
- [ ] **`requirements.txt` et version de Python du prof** : remplacer le fichier d'exemple par celui de l'enseignant, ajuster `Dockerfile` (`FROM python:3.12-slim`) si la version diffère. Si une bibliothèque change (JWT, hachage), adapter `app/core/security.py`, tests à l'appui.
- [ ] **Migration initiale** : un seul de vous la génère, l'autre la relit.
  ```bash
  docker compose up -d db
  alembic revision --autogenerate -m "schema initial"
  alembic upgrade head
  python -m app.seed
  ```
  Vérifier à la main le fichier généré (types, `unique`, clés étrangères), puis le **committer tout de suite**.
- [ ] **Schémas communs** : écrire ensemble la pagination `{items, total, limit, offset}` (limit 20 par défaut, 100 max, offset 0), car clients, commandes, livraisons et impayés l'utilisent.
- [ ] **Décisions de la section 2** ci-dessous.
- [ ] **Git** : dépôt créé, branche `main` protégée, règles de [`CONTRIBUTING.md`](../CONTRIBUTING.md) lues par les deux.
- [ ] **Premier commit** : tout ce qui précède dans `main`. Ensuite, chacun travaille sur sa branche.

## 2. Décisions à prendre ensemble (et à noter dans le README)

1. **Numéro de commande (RG5)** : « identifiant sur 5 chiffres » = l'`id` de la commande en base (ce que suppose `formater_numero(annee, commande.id)`) ou un compteur qui repart à 1 chaque année ? Avec l'`id`, il faut un `flush()` avant de fixer le numéro. Choisir et tester.
2. **Qui peut créer/modifier un client (routes 7 et 10)** : le tableau des routes dit « Tous », la section 4 attribue ces actions à l'accueil. Le plus sûr est de suivre le tableau des routes ; à confirmer auprès de l'enseignant en cas de doute.
3. **« Encaissé » et commandes annulées** : le chiffre d'affaires exclut les commandes annulées, mais « encaissé » est défini comme le total des paiements reçus. Une commande annulée avec acompte compte-t-elle dans l'encaissé ? À trancher, une seule fois, pour les routes 39 et 40.
4. **Rôles de la route 28 (changement de statut)** : tous les rôles y accèdent, mais le tailleur ne peut pas annuler (RG14). Le contrôle se fait dans le service, pas dans le routeur.

## 3. Ce que chacun fournit à l'autre (contrats)

On écrit ces fonctions **en premier**, avec leur signature figée, avant le reste.

| Fournisseur | Fonction (dans `app/services/`) | Utilisée par |
|---|---|---|
| Massamba | `commandes_service.recalculer_montants(commande)` : total, payé, solde, contrôles RG7 | paiements (Sine), commandes |
| Massamba | `commandes_service.enregistrer_changement_statut(db, commande, nouveau, commentaire, utilisateur)` : écrit l'historique (RG15) | livraison (Sine, RG20), route 28 |
| Massamba | `calculer_solde`, `est_en_retard`, `verifier_transition` (**déjà prêtes**) | paiements, livraisons, statistiques |
| Sine | accès en lecture aux `Mesure` d'un client (modèle `Mesure`, `CHAMPS_MESURES`) | commandes : RG9 |

Règle : si une signature change, on prévient l'autre **avant** de merger.

## 4. Étapes 1 à 3 : un palier à la fois

L'énoncé demande de terminer un palier avant de passer au suivant. En binôme, on le respecte pour la **fusion** dans `main` : on peut préparer le palier suivant sur sa branche, mais on ne merge un palier qu'une fois le précédent entièrement vert.

### Étape 1 : palier 1 (routes 1 à 17)
- **Massamba** : utilisateurs (3 à 6, RG21, RG24), clients (7 à 13, RG1, RG4), catalogue (14 à 17).
- **Sine**, en parallèle : tests des droits par rôle (modèle ci-dessous), puis prépare les schémas et le service des mesures (palier 2).
- **Fin d'étape (ensemble)** : revue croisée des PR, `pytest` vert, tour de Swagger.

### Étape 2 : palier 2 (routes 18 à 34)
- **Massamba** : commandes (24 à 31, RG5 à RG15), en commençant par les deux fonctions de contrat du tableau ci-dessus.
- **Sine** : mesures (18 à 23, RG2 à RG4), puis paiements (32 à 34, RG16, RG17) dès que `recalculer_montants` est mergée.
- **Fin d'étape (ensemble)** : scénario de l'annexe A, étapes 1 à 8, joué à deux dans Swagger.

### Étape 3 : palier 3 (routes 35 à 44)
- **Sine** : livraisons (35 à 38, RG18 à RG20), statistiques (39 à 43).
- **Massamba** : Docker de bout en bout (`docker compose up --build` sur une machine propre), seed, README, relecture des statistiques.
- **Fin d'étape (ensemble)** : scénario complet de l'annexe A (étapes 1 à 10).

## 5. Étape finale, ensemble

- [ ] Tests : au moins un par règle de gestion importante, et un test des droits par rôle.
- [ ] Cloner le dépôt **dans un dossier vide**, suivre uniquement le README, lancer les tests (vérification demandée en section 9).
- [ ] README complet : installation, lancement, comptes de test, liste des routes réalisées, décisions de la section 2.
- [ ] Répétition de la démonstration : chacun sait expliquer **tout** le code, pas seulement sa partie.

## 6. Modèle de test des droits (à copier)

Un test par rôle sur une route qu'il ne doit pas pouvoir appeler, avec les fixtures de `tests/conftest.py` (`headers_admin`, `headers_accueil`, `headers_tailleur`) :

```python
def test_accueil_ne_peut_pas_prendre_de_mesures(client, headers_accueil):
    r = client.post("/api/v1/clients/1/mesures", json={"tour_cou": 38}, headers=headers_accueil)
    assert r.status_code == 403          # annexe A, étape 2

def test_sans_jeton_401(client):
    assert client.get("/api/v1/clients").status_code == 401
```

## 7. Point d'attention dans le code existant

`verifier_transition` répond « Cette commande est à un statut final » quand on tente de quitter `terminee` vers autre chose que `livree`. Or `terminee` n'est pas un statut final : le message devrait dire que seule la confirmation de livraison peut la faire évoluer. À corriger (et à tester) à l'étape 2.

## 8. Rituels

- **10 minutes chaque jour** : ce qui est fait, ce qui bloque, ce qui change dans un contrat.
- **Toute PR est relue par l'autre** avant le merge.
- **Avant de dormir** : `git pull --rebase origin main`, `pytest`, `python -m scripts.avancement`.
