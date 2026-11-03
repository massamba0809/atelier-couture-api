# Règles de collaboration

Elles servent à une seule chose : que le code ressemble à celui d'une seule personne.

## Git

- `main` est protégée : on ne pousse **jamais** dessus directement.
- Une branche par fonctionnalité : `feat/clients`, `feat/paiements`, `fix/telephone-doublon`.
- Une **Pull Request** par fonctionnalité, **relue par l'autre** avant le merge.
- Avant d'ouvrir une PR : `git pull --rebase origin main`, puis `pytest`.
- Commits courts et clairs, en français : `feat(paiements): refuse un paiement supérieur au solde`.
- Jamais de `.env`, de mot de passe ou de clé dans Git.

## Migrations Alembic (source n°1 de conflits)

- Si on modifie un modèle, **on crée la migration dans la même PR** : `alembic revision --autogenerate -m "..."`.
- On relit toujours le fichier généré avant de le committer.
- Deux migrations ne doivent jamais partir du même point : si l'autre a mergé une migration avant vous, rebasez, puis régénérez la vôtre.
- Le schéma doit se créer avec `alembic upgrade head`, **jamais** avec `create_all` (sauf dans les tests).

## Architecture (section 3 de l'énoncé)

| Couche | Rôle | Interdit |
|---|---|---|
| `routers/` | vérifie les droits, appelle un service, fait le `commit` | toute règle de gestion |
| `services/` | toute la logique métier, en fonctions testables ; ne font que `flush()` | connaître HTTP (on lève `Conflit`, `Introuvable`, `DonneesInvalides`...) |
| `schemas/` | Pydantic : un schéma pour créer, un pour modifier, un pour lire | renvoyer un modèle SQLAlchemy tel quel (surtout pas `mot_de_passe_hash`) |
| `models/` | tables SQLAlchemy | logique métier |

## Conventions

- Noms de routes, champs et statuts **en français, exactement comme dans l'énoncé** : la correction s'appuie dessus.
- Erreurs au format `{"detail": "message en français, clair et actionnable"}`, avec le bon code (401, 403, 404, 409, 422).
- Listes paginées : `{"items": [...], "total": n, "limit": n, "offset": n}` (limit 20 par défaut, 100 maximum).
- PATCH : ne change que les champs envoyés.
- Montants : entiers en FCFA. Mesures : nombres en centimètres.
- Fichiers et fonctions en `snake_case`, schémas en `XxxCreate`, `XxxUpdate`, `XxxRead`.

## Une route est « terminée » quand

1. Elle est dans le bon routeur, avec le bon rôle (`Depends(require_roles(...))`).
2. Les règles de gestion associées sont dans un **service**, pas dans le routeur.
3. Les codes de retour de l'énoncé sont respectés (y compris les cas d'erreur).
4. Il y a au moins un test (cas nominal + le cas d'erreur le plus important).
5. `pytest` est vert, `python -m scripts.avancement` la montre ✓, la PR est relue.

## Tests

- `pytest` utilise SQLite en mémoire (autorisé pour les tests) ; le rendu final tourne sur PostgreSQL.
- Fixtures disponibles : `client`, `db`, `headers_admin`, `headers_accueil`, `headers_tailleur`.
- Les fonctions pures (calculs, workflow) se testent sans base, comme dans `tests/test_regles_commandes.py`.
