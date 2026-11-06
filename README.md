# API de gestion d'un atelier de couture

Projet final du module « Développement d'API avec FastAPI et PostgreSQL ».
API REST pour gérer les clients, leurs mesures, les commandes, les paiements et les livraisons d'un atelier de couture, avec des droits différents selon le rôle (`admin`, `accueil`, `tailleur`).

**Binôme** : Massamba Fall Séne et Sine Seck.

**État** : les 44 routes de l'énoncé sont réalisées et testées (354 tests). Suivi détaillé des règles de gestion : [`docs/SUIVI.md`](docs/SUIVI.md).

## Pile technique

FastAPI · PostgreSQL · SQLAlchemy 2 · Alembic · Pydantic · JWT (PyJWT) · Argon2 · pytest · Docker.

## Installation

```bash
git clone <url-du-depot> atelier-couture-api
cd atelier-couture-api
cp .env.example .env          # puis remplir les valeurs
```

Dans `.env`, remplacer au minimum `SECRET_KEY` (générer une clé avec `python -c "import secrets; print(secrets.token_hex(32))"`) et les mots de passe. Les valeurs de `.env.example` suffisent pour un essai local.

### Avec Docker (recommandé)

```bash
docker compose up --build
```

L'API démarre sur http://localhost:8000 ; la documentation Swagger est sur http://localhost:8000/docs. Au démarrage, le conteneur applique les migrations (`alembic upgrade head`) puis crée l'administrateur et le catalogue de départ (`python -m app.seed`). Le seed peut être relancé sans créer de doublons.

- Après un `git pull`, relancer `docker compose up --build` pour reconstruire l'image (les données sont conservées dans le volume `pgdata`).
- Repartir d'une base vide : `docker compose down -v` (**efface toutes les données**), puis `docker compose up --build`.
- Si le port 5432 est déjà pris sur la machine, définir `POSTGRES_PORT_HOTE` dans `.env` (voir `.env.example`).

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
pytest                                   # en local (venv)
docker compose exec api pytest           # dans le conteneur, API démarrée
```

Les tests utilisent SQLite en mémoire : ils n'ont pas besoin de PostgreSQL et ne touchent pas à la base. Ils couvrent les règles de gestion RG1 à RG24, les droits par rôle (401 sans jeton, 403 pour un rôle insuffisant) et le scénario de l'annexe A.

## Comptes de test

L'administrateur est créé par `python -m app.seed` à partir des variables `ADMIN_EMAIL`, `ADMIN_PASSWORD` et `ADMIN_NOM_COMPLET` du fichier `.env`. Les comptes `accueil` et `tailleur` se créent ensuite par l'admin, avec `POST /api/v1/utilisateurs`.

| Rôle | E-mail | Mot de passe |
|---|---|---|
| admin | `admin@atelier.sn` (valeur de `ADMIN_EMAIL`) | `changez-moi-aussi` (valeur de `ADMIN_PASSWORD`) |
| accueil | `accueil@atelier.sn` | `accueil1234` |
| tailleur | `tailleur@atelier.sn` | `tailleur1234` |

Création des deux comptes (API démarrée, valeurs de `.env.example`) :

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -d "username=admin@atelier.sn&password=changez-moi-aussi" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

for role in accueil tailleur; do
  curl -s -X POST localhost:8000/api/v1/utilisateurs \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"email\": \"$role@atelier.sn\", \"nom_complet\": \"Compte $role\", \"mot_de_passe\": \"${role}1234\", \"role\": \"$role\"}"
done
```

Dans Swagger (`/docs`), le bouton **Authorize** accepte directement l'e-mail et le mot de passe (`username` = e-mail).

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

**Les 44 routes sont réalisées.** `python -m scripts.avancement` affiche l'état en direct. Les chemins sont préfixés par `/api/v1`, sauf `/health`.

| N° | Méthode | Chemin | Rôle | Palier | Responsable |
|---:|---|---|---|:-:|---|
| 1 | POST | `/api/v1/auth/login` | Public | 1 | Massamba |
| 2 | GET | `/api/v1/auth/me` | Connecté | 1 | Massamba |
| 3 | POST | `/api/v1/utilisateurs` | Admin | 1 | Massamba |
| 4 | GET | `/api/v1/utilisateurs` | Admin | 1 | Massamba |
| 5 | GET | `/api/v1/utilisateurs/{id}` | Admin | 1 | Massamba |
| 6 | PATCH | `/api/v1/utilisateurs/{id}` | Admin | 1 | Massamba |
| 7 | POST | `/api/v1/clients` | Tous | 1 | Massamba |
| 8 | GET | `/api/v1/clients` | Tous | 1 | Massamba |
| 9 | GET | `/api/v1/clients/{id}` | Tous | 1 | Massamba |
| 10 | PATCH | `/api/v1/clients/{id}` | Tous | 1 | Massamba |
| 11 | DELETE | `/api/v1/clients/{id}` | Admin | 1 | Massamba |
| 12 | GET | `/api/v1/clients/{id}/commandes` | Tous | 1 | Massamba |
| 13 | GET | `/api/v1/clients/{id}/resume` | Tous | 1 | Massamba |
| 14 | POST | `/api/v1/catalogue` | Admin | 1 | Massamba |
| 15 | GET | `/api/v1/catalogue` | Tous | 1 | Massamba |
| 16 | GET | `/api/v1/catalogue/{id}` | Tous | 1 | Massamba |
| 17 | PATCH | `/api/v1/catalogue/{id}` | Admin | 1 | Massamba |
| 18 | POST | `/api/v1/clients/{id}/mesures` | Tailleur | 2 | Sine |
| 19 | GET | `/api/v1/clients/{id}/mesures` | Tous | 2 | Sine |
| 20 | GET | `/api/v1/clients/{id}/mesures/derniere` | Tous | 2 | Sine |
| 21 | GET | `/api/v1/mesures/{id}` | Tous | 2 | Sine |
| 22 | PATCH | `/api/v1/mesures/{id}` | Tailleur | 2 | Sine |
| 23 | DELETE | `/api/v1/mesures/{id}` | Tailleur | 2 | Sine |
| 24 | POST | `/api/v1/commandes` | Accueil | 2 | Massamba |
| 25 | GET | `/api/v1/commandes` | Tous | 2 | Massamba |
| 26 | GET | `/api/v1/commandes/{id}` | Tous | 2 | Massamba |
| 27 | PATCH | `/api/v1/commandes/{id}` | Accueil | 2 | Massamba |
| 28 | POST | `/api/v1/commandes/{id}/statut` | Tous (RG13-14) | 2 | Massamba |
| 29 | GET | `/api/v1/commandes/{id}/historique` | Tous | 2 | Massamba |
| 30 | POST | `/api/v1/commandes/{id}/lignes` | Accueil | 2 | Massamba |
| 31 | DELETE | `/api/v1/commandes/{id}/lignes/{ligne_id}` | Accueil | 2 | Massamba |
| 32 | POST | `/api/v1/commandes/{id}/paiements` | Accueil | 2 | Sine |
| 33 | GET | `/api/v1/commandes/{id}/paiements` | Tous | 2 | Sine |
| 34 | DELETE | `/api/v1/paiements/{id}` | Admin | 2 | Sine |
| 35 | PUT | `/api/v1/commandes/{id}/livraison` | Accueil | 3 | Sine |
| 36 | GET | `/api/v1/commandes/{id}/livraison` | Tous | 3 | Sine |
| 37 | POST | `/api/v1/commandes/{id}/livraison/confirmer` | Accueil | 3 | Sine |
| 38 | GET | `/api/v1/livraisons` | Tous | 3 | Sine |
| 39 | GET | `/api/v1/statistiques/tableau-de-bord` | Admin | 3 | Sine |
| 40 | GET | `/api/v1/statistiques/chiffre-affaires` | Admin | 3 | Sine |
| 41 | GET | `/api/v1/statistiques/types-vetement` | Admin | 3 | Sine |
| 42 | GET | `/api/v1/statistiques/top-clients` | Admin | 3 | Sine |
| 43 | GET | `/api/v1/statistiques/impayes` | Admin | 3 | Sine |
| 44 | GET | `/health` | Public | 3 | Sine |

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
| Unicité (RG1, routes 3 et 14) | Téléphone comparé après normalisation ; e-mail des comptes et nom des prestations comparés sans tenir compte des majuscules (« Boubou » = « BOUBOU »). |
| Ressource inconnue dans le corps | `client_id` ou `type_vetement_id` inexistant → 404 (comme les routes de consultation). Mesure inexistante ou d'un autre client → 422 (RG9). |
| Suppression d'un client (RG4) | Refusée dès qu'il a une commande, même annulée (l'énoncé dit « a des commandes », sans exception). |
| Recherche de clients (route 8) | `q` cherche dans nom et prénom sans tenir compte des majuscules, et dans le téléphone sans séparateurs (« 77 12 » trouve « 771234567 »). |
| Résumé client (route 13) | `derniere_commande` est la date de la commande non annulée la plus récente ; `solde_du` = `chiffre_affaires` − `total_paye`. |
| Catalogue (routes 14 à 17) | `prix_base` et `delai_jours` sont des entiers ≥ 0. La liste (route 15) n'est pas paginée (catalogue court). Une prestation retirée reste consultable par la route 16. |
| Montants (RG7) | Recalculés par le serveur à chaque changement (`recalculer_montants`). Un changement refusé (422 ou 409) ne modifie rien. |
| Statut (route 28) | Le refus de droit passe en premier : un tailleur qui demande `annulee` reçoit 403 même si la transition serait interdite. Un commentaire vide ou blanc compte comme absent (RG14). |
| Historique (RG15) | Date du changement fixée par l'application (et non par `now()` SQL, identique dans toute une transaction PostgreSQL) : l'ordre chronologique reste exact. |
| Lignes (routes 30 et 31) | Ajouter une ligne ne recalcule pas la date de livraison prévue (modifiable par la route 27). Retirer une ligne qui laisserait une remise supérieure aux prestations → 422 ; total sous le déjà payé → 409. |
| Liste des commandes (route 25) | `date_min` et `date_max` portent sur la date de commande ; `numero` accepte une partie du numéro (ex. `00017`). `client_nom` = « Prénom Nom », partout dans l'API. |
| Versions (`requirements.txt`) | Aucune liste n'ayant été fournie, les versions exactes sont celles avec lesquelles toute la suite de tests passe (Python 3.12). |
