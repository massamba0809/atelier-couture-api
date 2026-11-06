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

Les 24 règles sont implémentées dans les services et testées.

| Réf. | Règle (résumé) | Responsable | Statut | Où (code · tests) |
|---|---|---|---|---|
| RG1 | Téléphone unique, normalisé (6 à 20 chiffres) | Massamba | Fait | `clients_service` · `test_clients.py` |
| RG2 | Une prise = au moins 1 mesure, chaque mesure 0 < x ≤ 300 | Sine | Fait | `schemas/mesure.py`, `mesures_service.modifier_mesure` · `test_schemas_mesures.py`, `test_mesures.py`, `test_routes_mesures.py` |
| RG3 | Historique conservé ; « dernières » = date la plus récente | Sine | Fait | `mesures_service.dernieres_mesures` · `test_mesures.py` |
| RG4 | Suppression refusée (409) : client avec commandes, mesure utilisée | Massamba + Sine | Fait | `clients_service.supprimer_client`, `mesures_service.supprimer_mesure` · `test_clients.py`, `test_mesures.py` |
| RG5 | Numéro `CMD-AAAA-NNNNN` | Massamba | Fait | `commandes_service.creer_commande` · `test_commandes.py` |
| RG6 | Prix par défaut = catalogue ; prestation inactive → 422 | Massamba | Fait | `commandes_service._construire_ligne` · `test_commandes.py` |
| RG7 | Montants calculés serveur ; remise ≤ somme ; total jamais < déjà payé (409) | Massamba | Fait | `commandes_service.recalculer_montants` · `test_commandes_contrat.py`, `test_commandes_suite.py` |
| RG8 | Date de livraison par défaut ; pas avant la date de commande (422) | Massamba | Fait | `commandes_service` · `test_commandes.py` |
| RG9 | Mesures de la commande = celles du client (422) ; défaut = dernières | Massamba | Fait | `commandes_service._choisir_mesure` · `test_commandes.py` |
| RG10 | Lignes modifiables seulement en `en_attente` ; au moins 1 ligne (409) | Massamba | Fait | `commandes_service` · `test_commandes_suite.py` |
| RG11 | « En retard » = date prévue dépassée et ni livrée ni annulée | Massamba | Fait | `commandes_service.est_en_retard` · `test_commandes.py` |
| RG12 | Commande livrée ou annulée non modifiable (409) | Massamba + Sine | Fait | `commandes_service`, `livraisons_service` · `test_commandes_suite.py`, `test_livraisons.py` |
| RG13 | Workflow des statuts ; `livree` seulement via la livraison | Massamba | Fait | `commandes_service.verifier_transition` · `test_commandes_suite.py` |
| RG14 | Tailleur ne peut pas annuler (403) ; annuler avec acompte exige un commentaire (422) | Massamba | Fait | `commandes_service.changer_statut` · `test_commandes_suite.py` |
| RG15 | Historique à chaque changement (1re ligne à la création) | Massamba | Fait | `commandes_service.enregistrer_changement_statut` · `test_commandes_contrat.py` |
| RG16 | Paiement > 0, ≤ solde (409), date non future (422), refusé si annulée (409) | Sine | Fait | `paiements_service.enregistrer_paiement` · `test_paiements.py` |
| RG17 | Annuler un paiement recalcule payé et solde | Sine | Fait | `paiements_service.annuler_paiement` · `test_paiements.py` |
| RG18 | Livraison à domicile exige une adresse ; replanifier ne crée pas de doublon | Sine | Fait | `livraisons_service.planifier_livraison` · `test_livraisons.py` |
| RG19 | Confirmer exige commande terminée ET soldée (409), sauf `autoriser_solde_impaye` | Sine | Fait | `livraisons_service.confirmer_livraison` · `test_livraisons.py` |
| RG20 | À la confirmation : `livree`, dates renseignées, livraison `retrait_atelier` auto | Sine | Fait | `livraisons_service.confirmer_livraison` · `test_livraisons.py` |
| RG21 | Mots de passe hachés (Argon2), ≥ 8 caractères, jamais renvoyés | Massamba | Fait | `core/security.py`, `schemas/utilisateur.py` · `test_utilisateurs.py`, `test_auth.py` |
| RG22 | JWT signé avec expiration ; compte désactivé refusé immédiatement | Massamba | Fait | `core/deps.get_current_user` · `test_auth.py` |
| RG23 | Même message 401, e-mail inconnu ou mot de passe faux | Massamba | Fait | `auth_service` · `test_auth.py` |
| RG24 | Un admin ne peut ni se désactiver ni retirer son rôle admin (409) | Massamba | Fait | `utilisateurs_service` · `test_utilisateurs.py` |

## Livrables (section 9 de l'énoncé)

- [x] Code de l'API organisé comme en section 3
- [x] `requirements.txt` avec versions exactes (aucun fichier fourni par l'enseignant : versions figées par le binôme)
- [x] Migrations Alembic (schéma initial complet)
- [x] `python -m app.seed` (admin + catalogue de l'annexe B)
- [x] Tests pytest : 1 test par règle importante + 1 test des droits par rôle
- [x] `Dockerfile` + `docker-compose.yml`
- [x] `.env.example` sans secret + `.gitignore` qui exclut `.env`
- [x] README : installation, lancement, comptes de test, liste des routes réalisées
- [ ] Vérifié : `docker compose up --build` sur une machine propre
- [ ] Vérifié : clone dans un dossier vide, README suivi pas à pas, tests verts
- [ ] Répétition du scénario de démonstration (annexe A) à deux
