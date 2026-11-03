# Suivi du projet

Répartition **proposée** (à ajuster ensemble). L'avancement des routes se lit en direct avec :

```bash
python -m scripts.avancement
```

## Routes (44)

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

## Règles de gestion (24)

Statut : **Fait** = implémenté et testé · **Partiel** = la fonction pure existe, il reste le branchement dans les routes · **À faire**.

| Réf. | Règle (résumé) | Responsable | Statut | Où / reste à faire |
|---|---|---|---|---|
| RG1 | Téléphone unique, normalisé (6 à 20 chiffres) | Massamba | Partiel | `clients_service.normaliser_telephone` ✔ testée · doublon 409 à faire (routes 7, 10) |
| RG2 | Une prise = au moins 1 mesure, chaque mesure 0 < x ≤ 300 | Sine | À faire | schéma Pydantic + `mesures_service` (`CHAMPS_MESURES`) |
| RG3 | Historique conservé ; « dernières » = date la plus récente | Sine | À faire | `mesures_service` (route 20) |
| RG4 | Suppression refusée (409) : client avec commandes, mesure utilisée | Massamba + Sine | À faire | route 11 (Massamba), route 23 (Sine) |
| RG5 | Numéro `CMD-AAAA-NNNNN` | Massamba | Partiel | `formater_numero` ✔ testée · génération à la création à faire |
| RG6 | Prix par défaut = catalogue ; prestation inactive → 422 | Massamba | À faire | `commandes_service` (route 24, 30) |
| RG7 | Montants calculés serveur ; remise ≤ somme ; total jamais < déjà payé (409) | Massamba | Partiel | `calculer_total`, `calculer_solde` ✔ · contrôles + `recalculer_montants` à faire |
| RG8 | Date de livraison par défaut ; pas avant la date de commande (422) | Massamba | Partiel | `date_livraison_par_defaut` ✔ · contrôle 422 à faire |
| RG9 | Mesures de la commande = celles du client (422) ; défaut = dernières | Massamba | À faire | `commandes_service` (route 24, 27) |
| RG10 | Lignes modifiables seulement en `en_attente` ; au moins 1 ligne (409) | Massamba | À faire | routes 30, 31 |
| RG11 | « En retard » = date prévue dépassée et ni livrée ni annulée | Massamba | Partiel | `est_en_retard` ✔ · à exposer dans routes 25, 26 |
| RG12 | Commande livrée ou annulée non modifiable (409) | Massamba | À faire | routes 27, 30, 31 (et 35 côté Sine) |
| RG13 | Workflow des statuts ; `livree` seulement via la livraison | Massamba | Partiel | `verifier_transition` ✔ testée · route 28 à faire |
| RG14 | Tailleur ne peut pas annuler (403) ; annuler avec acompte exige un commentaire (422) | Massamba | À faire | route 28 |
| RG15 | Historique à chaque changement (1re ligne à la création) | Massamba | À faire | `commandes_service` (fonction partagée avec la livraison) |
| RG16 | Paiement > 0, ≤ solde (409), date non future (422), refusé si annulée (409) | Sine | À faire | `paiements_service` (route 32) |
| RG17 | Annuler un paiement recalcule payé et solde | Sine | À faire | route 34 |
| RG18 | Livraison à domicile exige une adresse ; replanifier ne crée pas de doublon | Sine | À faire | route 35 |
| RG19 | Confirmer exige commande terminée ET soldée (409), sauf `autoriser_solde_impaye` | Sine | À faire | route 37 |
| RG20 | À la confirmation : `livree`, dates renseignées, livraison `retrait_atelier` auto | Sine | À faire | route 37 |
| RG21 | Mots de passe hachés (Argon2), ≥ 8 caractères, jamais renvoyés | Massamba | Partiel | hachage ✔ (`security.py`) · longueur min dans le schéma à faire |
| RG22 | JWT signé avec expiration ; compte désactivé refusé immédiatement | Massamba | Fait | `deps.get_current_user` · `tests/test_auth.py` |
| RG23 | Même message 401, e-mail inconnu ou mot de passe faux | Massamba | Fait | `auth_service` · `tests/test_auth.py` |
| RG24 | Un admin ne peut ni se désactiver ni retirer son rôle admin (409) | Massamba | À faire | route 6 |

## Livrables (section 9 de l'énoncé)

- [ ] Code de l'API organisé comme en section 3
- [ ] `requirements.txt` du prof (versions exactes)
- [ ] Migrations Alembic (schéma initial complet)
- [ ] `python -m app.seed` (admin + catalogue de l'annexe B)
- [ ] Tests pytest : 1 test par règle importante + 1 test des droits par rôle
- [ ] `Dockerfile` + `docker-compose.yml` (`docker compose up --build`)
- [ ] `.env.example` sans secret + `.gitignore` qui exclut `.env`
- [ ] README : installation, lancement, comptes de test, liste des routes réalisées
- [ ] Répétition du scénario de démonstration (annexe A)
