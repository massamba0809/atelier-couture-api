# Suivi du projet

**Les 44 routes sont réalisées.** L'avancement des routes se lit en direct avec :

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

Toutes les règles sont **implémentées et testées**. Colonne « Tests » : fichiers de `tests/` qui les vérifient.

| Réf. | Règle (résumé) | Responsable | Statut | Où | Tests |
|---|---|---|---|---|---|
| RG1 | Téléphone unique, normalisé (6 à 20 chiffres) | Massamba | Fait | `clients_service` (routes 7, 10) | `test_clients`, `test_regles_commandes` |
| RG2 | Une prise = au moins 1 mesure, chaque mesure 0 < x ≤ 300 | Sine | Fait | `schemas/mesure`, `mesures_service` (routes 18, 22) | `test_schemas_mesures`, `test_mesures`, `test_routes_mesures` |
| RG3 | Historique conservé ; « dernières » = date la plus récente | Sine | Fait | `mesures_service.dernieres_mesures` (routes 19, 20) | `test_mesures` |
| RG4 | Suppression refusée (409) : client avec commandes, mesure utilisée | Massamba + Sine | Fait | routes 11 et 23 | `test_clients`, `test_mesures`, `test_routes_mesures` |
| RG5 | Numéro `CMD-AAAA-NNNNN` | Massamba | Fait | `commandes_service.creer_commande` (route 24) | `test_commandes`, `test_regles_commandes` |
| RG6 | Prix par défaut = catalogue ; prestation inactive → 422 | Massamba | Fait | `_construire_ligne` (routes 24, 30) | `test_commandes`, `test_commandes_suite` |
| RG7 | Montants calculés serveur ; remise ≤ somme ; total jamais < déjà payé (409) | Massamba | Fait | `recalculer_montants` (routes 24, 27, 30, 31, 32, 34) | `test_commandes_contrat`, `test_commandes`, `test_commandes_suite` |
| RG8 | Date de livraison par défaut ; pas avant la date de commande (422) | Massamba | Fait | routes 24, 27 (et 35 côté Sine) | `test_commandes`, `test_commandes_suite` |
| RG9 | Mesures de la commande = celles du client (422) ; défaut = dernières | Massamba | Fait | `_choisir_mesure` (routes 24, 27) | `test_commandes`, `test_commandes_suite` |
| RG10 | Lignes modifiables seulement en `en_attente` ; au moins 1 ligne (409) | Massamba | Fait | routes 30, 31 | `test_commandes_suite` |
| RG11 | « En retard » = date prévue dépassée et ni livrée ni annulée | Massamba | Fait | `est_en_retard` (routes 25, 26, 39, 43) | `test_commandes`, `test_regles_commandes` |
| RG12 | Commande livrée ou annulée non modifiable (409) | Massamba | Fait | routes 27, 30, 31 (et 35 côté Sine) | `test_commandes_suite`, `test_livraisons` |
| RG13 | Workflow des statuts ; `livree` seulement via la livraison | Massamba | Fait | `verifier_transition` (route 28) | `test_commandes_suite`, `test_regles_commandes` |
| RG14 | Tailleur ne peut pas annuler (403) ; annuler avec acompte exige un commentaire (422) | Massamba | Fait | `changer_statut` (route 28) | `test_commandes_suite` |
| RG15 | Historique à chaque changement (1re ligne à la création) | Massamba | Fait | `enregistrer_changement_statut` (routes 24, 28, 37) | `test_commandes_contrat`, `test_commandes_suite`, `test_livraisons` |
| RG16 | Paiement > 0, ≤ solde (409), date non future (422), refusé si annulée (409) | Sine | Fait | `paiements_service` (route 32) | `test_paiements` |
| RG17 | Annuler un paiement recalcule payé et solde | Sine | Fait | route 34 | `test_paiements`, `test_commandes_contrat` |
| RG18 | Livraison à domicile exige une adresse ; replanifier ne crée pas de doublon | Sine | Fait | route 35 | `test_livraisons` |
| RG19 | Confirmer exige commande terminée ET soldée (409), sauf `autoriser_solde_impaye` | Sine | Fait | route 37 | `test_livraisons` |
| RG20 | À la confirmation : `livree`, dates renseignées, livraison `retrait_atelier` auto | Sine | Fait | route 37 | `test_livraisons`, `test_commandes_contrat` |
| RG21 | Mots de passe hachés (Argon2), ≥ 8 caractères, jamais renvoyés | Massamba | Fait | `security.py`, `schemas/utilisateur` (routes 3, 6) | `test_auth`, `test_utilisateurs` |
| RG22 | JWT signé avec expiration ; compte désactivé refusé immédiatement | Massamba | Fait | `deps.get_current_user` | `test_auth`, `test_utilisateurs` |
| RG23 | Même message 401, e-mail inconnu ou mot de passe faux | Massamba | Fait | `auth_service` (route 1) | `test_auth` |
| RG24 | Un admin ne peut ni se désactiver ni retirer son rôle admin (409) | Massamba | Fait | `utilisateurs_service` (route 6) | `test_utilisateurs` |

## Livrables (section 9 de l'énoncé)

- [x] Code de l'API organisé comme en section 3 (routers, services, schemas, models)
- [x] `requirements.txt` avec les versions exactes (aucune liste fournie par l'enseignant : versions validées par la suite de tests)
- [x] Migrations Alembic (schéma initial complet)
- [x] `python -m app.seed` (admin + catalogue de l'annexe B), relançable sans doublon
- [x] Tests pytest : au moins un test par règle (tableau ci-dessus) + tests des droits par rôle (354 tests)
- [x] `Dockerfile` + `docker-compose.yml` : `docker compose up --build` vérifié sur une base vide (migrations, seed, API, tests dans le conteneur)
- [x] `.env.example` sans secret + `.gitignore` qui exclut `.env`
- [x] README : installation, lancement, comptes de test, liste des routes réalisées, décisions
- [x] Scénario de l'annexe A (étapes 1 à 10) joué par HTTP sur PostgreSQL
- [ ] Vérification finale **ensemble** : cloner le dépôt GitHub dans un dossier vide, suivre uniquement le README, lancer les tests
- [ ] Répétition de la démonstration (annexe A dans Swagger) : chacun sait expliquer tout le code
