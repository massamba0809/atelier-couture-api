# API de gestion d'un atelier de couture

Projet final du module « Développement d'API avec FastAPI et PostgreSQL ».
API REST pour gérer les clients, leurs mesures, les commandes, les paiements et les livraisons d'un atelier de couture, avec des droits différents selon le rôle (`admin`, `accueil`, `tailleur`).

**Binôme** : Massamba Fall Séne et Sine Seck.

> Ce README est un squelette : il sera complété au fil du projet (comptes de test, liste des routes réalisées, décisions prises). Voir [`docs/PLAN_DE_TRAVAIL.md`](docs/PLAN_DE_TRAVAIL.md) et [`docs/SUIVI.md`](docs/SUIVI.md).

## Pile technique

FastAPI · PostgreSQL · SQLAlchemy 2 · Alembic · Pydantic · JWT (PyJWT) · Argon2 · pytest · Docker.

## Installation

```bash
git clone <url-du-depot> atelier-couture-api
cd atelier-couture-api
cp .env.example .env          # puis remplir les valeurs
```

### Avec Docker (recommandé)

```bash
docker compose up --build
```

L'API démarre sur http://localhost:8000 ; la documentation Swagger est sur http://localhost:8000/docs. Au démarrage, le conteneur applique les migrations (`alembic upgrade head`) puis crée l'administrateur et le catalogue de départ (`python -m app.seed`).

### Sans Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d db        # ou un PostgreSQL local
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Dans `.env`, `DATABASE_URL` doit pointer vers `localhost` en local et vers `db` dans Docker (déjà géré par `docker-compose.yml`).

## Tests

```bash
pytest
```

Les tests utilisent SQLite en mémoire.

## Comptes de test

L'administrateur est créé par `python -m app.seed` à partir des variables `ADMIN_EMAIL`, `ADMIN_PASSWORD` et `ADMIN_NOM_COMPLET` du fichier `.env`. Les comptes `accueil` et `tailleur` se créent ensuite avec `POST /api/v1/utilisateurs` (réservé à l'admin).

| Rôle | E-mail | Mot de passe |
|---|---|---|
| admin | _(valeur de `ADMIN_EMAIL`)_ | _(valeur de `ADMIN_PASSWORD`)_ |
| accueil | `accueil@atelier.sn` | `accueil123` |
| tailleur | `tailleur@atelier.sn` | `tailleur123` |

Pour créer les deux comptes de démonstration : se connecter en admin dans Swagger (**Authorize**), puis `POST /api/v1/utilisateurs` avec :

```json
{"email": "accueil@atelier.sn", "nom_complet": "Awa Accueil", "mot_de_passe": "accueil123", "role": "accueil"}
{"email": "tailleur@atelier.sn", "nom_complet": "Mamadou Tailleur", "mot_de_passe": "tailleur123", "role": "tailleur"}
```

## Organisation du code

```
app/
  main.py            application FastAPI, préfixe /api/v1, gestion des erreurs
  seed.py            python -m app.seed : admin + catalogue de l'annexe B
  core/              configuration, base de données, sécurité, dépendances, erreurs
  models/            modèles SQLAlchemy (+ enums.py)
  schemas/           schémas Pydantic (création / modification / lecture)
  routers/           un fichier par domaine : droits + appel au service + commit
  services/          règles de gestion (testables sans base)
alembic/             migrations
tests/               tests pytest
docs/                plan de travail et suivi
scripts/avancement.py   routes réalisées sur les 44
```

## Routes réalisées

**Les 44 routes de l'énoncé sont réalisées et testées** (`python -m scripts.avancement` affiche l'état en direct).

| Domaine | Routes | Règles | Responsable |
|---|---|---|---|
| Authentification | 1-2 | RG22, RG23 | Massamba |
| Utilisateurs | 3-6 | RG21, RG24 | Massamba |
| Clients | 7-13 | RG1, RG4 | Massamba |
| Catalogue | 14-17 | — | Massamba |
| Mesures | 18-23 | RG2, RG3, RG4 | Sine |
| Commandes | 24-31 | RG5 à RG15 | Massamba |
| Paiements | 32-34 | RG16, RG17 | Sine |
| Livraisons | 35-38 | RG18, RG19, RG20 | Sine |
| Statistiques | 39-43 | Indicateurs de la section 6 | Sine |
| Santé | 44 | — | Sine |

Le détail route par route et règle par règle est dans [`docs/SUIVI.md`](docs/SUIVI.md).

## Décisions de conception

Points de l'énoncé ambigus ou contradictoires, tranchés par le binôme :

| Sujet | Décision |
|---|---|
| Connexion | Par e-mail (route 1 : `username` = e-mail) : le modèle `Utilisateur` n'a pas de téléphone, contrairement à ce que suggère la section 4. |
| Numéro de commande (RG5) | `CMD-AAAA-NNNNN`, où `NNNNN` est l'`id` de la commande en base. |
| Création / modification d'un client | Ouvertes à tous les rôles, conformément au tableau des routes (7 et 10). |
| Annulation par le tailleur (route 28) | La route est ouverte à tous ; le refus (403, RG14) est fait dans le service. |
| « Encaissé » (statistiques) | Inclut les paiements des commandes annulées : l'argent a bien été reçu (remboursement géré hors API). |
| Livraison avec solde impayé (RG19) | L'historique reçoit la mention « Livré avec solde impayé de X FCFA ». |
| Confirmation de livraison (route 37) | Renvoie la livraison ; la commande passe à `livree` (consultable par la route 26). |
| Date de livraison prévue (route 35) | Refusée si elle précède la date de commande (422), par cohérence avec RG8. |
| Dernières mesures (RG3) | Date de prise la plus récente ; à date égale, la dernière saisie (plus grand `id`). |
| Statistiques | `nb_commandes_mois` exclut les commandes annulées ; `livraisons_du_jour` compte les livraisons planifiées pour aujourd'hui ; granularité par défaut : `jour`. |
| `requirements.txt` | Aucun fichier fourni par l'enseignant : versions exactes figées par le binôme (Python 3.12). |
