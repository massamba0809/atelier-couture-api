"""Routes 32 à 34 : paiements. RG16, RG17, droits par rôle (annexe A, étapes 6 et 8)."""
from datetime import date, timedelta

import pytest

from app.models.catalogue import TypeVetement
from app.models.client import Client
from app.models.commande import Commande, LigneCommande
from app.models.enums import Role, Statut
from app.services.commandes_service import recalculer_montants
from tests.conftest import creer_utilisateur

URL_COMMANDES = "/api/v1/commandes"
URL_PAIEMENTS = "/api/v1/paiements"


@pytest.fixture()
def commande(db) -> Commande:
    """2 boubous à 35 000 + 1 pantalon à 12 000, remise 5 000 → total 77 000, rien de payé."""
    auteur = creer_utilisateur(db, Role.accueil, email="auteur-paiements@atelier.sn")
    cliente = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    boubou = TypeVetement(nom="Boubou", prix_base=35_000, delai_jours=10)
    pantalon = TypeVetement(nom="Pantalon", prix_base=12_000, delai_jours=4)
    db.add_all([cliente, boubou, pantalon])
    db.flush()
    cmd = Commande(
        numero="CMD-2026-00001", client_id=cliente.id, statut=Statut.en_attente,
        date_livraison_prevue=date.today() + timedelta(days=10), remise=5_000,
        cree_par_id=auteur.id,
    )
    cmd.lignes.append(LigneCommande(type_vetement_id=boubou.id, quantite=2, prix_unitaire=35_000))
    cmd.lignes.append(LigneCommande(type_vetement_id=pantalon.id, quantite=1, prix_unitaire=12_000))
    db.add(cmd)
    recalculer_montants(cmd)
    db.commit()
    return cmd


def payer(client, commande, headers, montant, **autres):
    return client.post(
        f"{URL_COMMANDES}/{commande.id}/paiements",
        json={"montant": montant, "mode": "wave", **autres},
        headers=headers,
    )


# --- Route 32 : encaisser (RG16) ----------------------------------------------


def test_acompte_wave_201_et_solde_recalcule(client, db, headers_accueil, commande):  # annexe A, ét. 6
    r = payer(client, commande, headers_accueil, 20_000, reference="WAVE-123")
    assert r.status_code == 201
    corps = r.json()
    assert corps["montant"] == 20_000 and corps["mode"] == "wave"
    assert corps["date_paiement"] == date.today().isoformat()
    db.refresh(commande)
    assert (commande.montant_paye, commande.solde) == (20_000, 57_000)


def test_deux_paiements_successifs_cumules(client, db, headers_accueil, commande):
    payer(client, commande, headers_accueil, 20_000)
    payer(client, commande, headers_accueil, 30_000)
    db.refresh(commande)
    assert (commande.montant_paye, commande.solde) == (50_000, 27_000)


def test_paiement_superieur_au_solde_409(client, headers_accueil, commande):  # annexe A, étape 6
    r = payer(client, commande, headers_accueil, 77_001)
    assert r.status_code == 409
    assert "solde restant (77000 FCFA)" in r.json()["detail"]


def test_payer_exactement_le_solde_accepte(client, db, headers_accueil, commande):  # annexe A, ét. 8
    assert payer(client, commande, headers_accueil, 77_000).status_code == 201
    db.refresh(commande)
    assert commande.solde == 0


@pytest.mark.parametrize("montant", [0, -500])
def test_montant_non_positif_422(client, headers_accueil, commande, montant):  # RG16
    assert payer(client, commande, headers_accueil, montant).status_code == 422


def test_date_future_422(client, headers_accueil, commande):  # RG16
    demain = (date.today() + timedelta(days=1)).isoformat()
    r = payer(client, commande, headers_accueil, 10_000, date_paiement=demain)
    assert r.status_code == 422
    assert "futur" in r.json()["detail"]


def test_date_passee_acceptee(client, headers_accueil, commande):
    hier = (date.today() - timedelta(days=1)).isoformat()
    r = payer(client, commande, headers_accueil, 10_000, date_paiement=hier)
    assert r.status_code == 201
    assert r.json()["date_paiement"] == hier


def test_commande_annulee_409(client, db, headers_accueil, commande):  # RG16
    commande.statut = Statut.annulee
    db.commit()
    r = payer(client, commande, headers_accueil, 10_000)
    assert r.status_code == 409
    assert "annulée" in r.json()["detail"]


def test_mode_inconnu_422(client, headers_accueil, commande):
    r = client.post(
        f"{URL_COMMANDES}/{commande.id}/paiements",
        json={"montant": 10_000, "mode": "carte_bleue"},
        headers=headers_accueil,
    )
    assert r.status_code == 422


def test_commande_inconnue_404(client, headers_accueil):
    r = client.post(
        f"{URL_COMMANDES}/999/paiements", json={"montant": 1_000, "mode": "especes"},
        headers=headers_accueil,
    )
    assert r.status_code == 404


def test_tailleur_ne_peut_pas_encaisser_403(client, headers_tailleur, commande):
    assert payer(client, commande, headers_tailleur, 10_000).status_code == 403


def test_sans_jeton_401(client, commande):
    assert payer(client, commande, {}, 10_000).status_code == 401


# --- Route 33 : lister --------------------------------------------------------


def test_liste_dans_l_ordre_de_saisie(client, headers_accueil, headers_tailleur, commande):
    premier = payer(client, commande, headers_accueil, 20_000).json()
    second = payer(client, commande, headers_accueil, 10_000).json()
    r = client.get(f"{URL_COMMANDES}/{commande.id}/paiements", headers=headers_tailleur)
    assert r.status_code == 200  # tout utilisateur connecté
    assert [p["id"] for p in r.json()] == [premier["id"], second["id"]]


# --- Route 34 : annuler (RG17) ------------------------------------------------


def test_admin_annule_un_paiement_204_et_solde_recalcule(
    client, db, headers_accueil, headers_admin, commande
):  # RG17
    p1 = payer(client, commande, headers_accueil, 20_000).json()
    payer(client, commande, headers_accueil, 30_000)
    r = client.delete(f"{URL_PAIEMENTS}/{p1['id']}", headers=headers_admin)
    assert r.status_code == 204
    db.refresh(commande)
    assert (commande.montant_paye, commande.solde) == (30_000, 47_000)


def test_annuler_paiement_inconnu_404(client, headers_admin):
    assert client.delete(f"{URL_PAIEMENTS}/999", headers=headers_admin).status_code == 404


def test_accueil_ne_peut_pas_annuler_un_paiement_403(client, headers_accueil, commande):
    p = payer(client, commande, headers_accueil, 20_000).json()
    assert client.delete(f"{URL_PAIEMENTS}/{p['id']}", headers=headers_accueil).status_code == 403
