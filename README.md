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
| accueil | _à créer_ | _à compléter_ |
| tailleur | _à créer_ | _à compléter_ |

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

À compléter en fin de projet : `python -m scripts.avancement` affiche l'état en direct.

## Décisions de conception

À compléter (voir la section 2 de `docs/PLAN_DE_TRAVAIL.md`).
