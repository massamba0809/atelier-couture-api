"""Routes 7 à 13 : clients. RG1 (téléphone unique et normalisé), RG4 (suppression), droits par rôle."""
from datetime import date

import pytest
from sqlalchemy import select

from app.models.client import Client
from app.models.commande import Commande
from app.models.enums import Role, Statut
from app.models.mesure import Mesure
from tests.conftest import creer_utilisateur

URL = "/api/v1/clients"
FATOU = {"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"}


@pytest.fixture()
def fatou(client, headers_accueil) -> dict:
    r = client.post(URL, json=FATOU, headers=headers_accueil)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def auteur(db):
    """Utilisateur noté comme créateur des commandes et des mesures insérées en base."""
    return creer_utilisateur(db, Role.tailleur, email="auteur@atelier.sn")


def inserer_commande(db, client_id, auteur, numero, statut=Statut.en_attente,
                     total=10_000, paye=0, jour=date(2026, 1, 10)):
    commande = Commande(
        numero=numero, client_id=client_id, statut=statut, date_commande=jour,
        date_livraison_prevue=jour, montant_total=total, montant_paye=paye, cree_par_id=auteur.id,
    )
    db.add(commande)
    db.commit()
    return commande


def inserer_mesure(db, client_id, auteur):
    mesure = Mesure(client_id=client_id, prise_par_id=auteur.id, tour_cou=38)
    db.add(mesure)
    db.commit()
    return mesure


# Route 7 : POST /clients
def test_creer_client_201_telephone_normalise(client, headers_accueil):  # RG1
    r = client.post(URL, json=FATOU, headers=headers_accueil)
    assert r.status_code == 201
    corps = r.json()
    assert corps["telephone"] == "771234567"
    assert corps["nom"] == "Diop" and corps["prenom"] == "Fatou" and corps["genre"] == "femme"
    assert {"id", "created_at", "updated_at", "email", "adresse", "notes"} <= corps.keys()


def test_meme_numero_autre_ecriture_409(client, headers_accueil, fatou):  # RG1, annexe A étape 1
    r = client.post(URL, json={**FATOU, "prenom": "Awa", "telephone": "771234567"}, headers=headers_accueil)
    assert r.status_code == 409
    assert r.json() == {"detail": "Un client existe déjà avec le téléphone 771234567."}


@pytest.mark.parametrize("telephone", ["12345", "77 12a 45 67", "+", "1" * 21])
def test_telephone_invalide_422(client, headers_accueil, telephone):  # RG1
    r = client.post(URL, json={**FATOU, "telephone": telephone}, headers=headers_accueil)
    assert r.status_code == 422
    assert "téléphone" in r.json()["detail"]


def test_telephone_international_accepte(client, headers_accueil):
    r = client.post(URL, json={**FATOU, "telephone": "+221 (77) 123-45.67"}, headers=headers_accueil)
    assert r.status_code == 201
    assert r.json()["telephone"] == "+221771234567"


def test_creer_client_champ_manquant_422(client, headers_accueil):
    r = client.post(URL, json={"nom": "Diop", "telephone": "771234567"}, headers=headers_accueil)
    assert r.status_code == 422
    assert "prenom : champ obligatoire" in r.json()["detail"]


@pytest.mark.parametrize("headers", ["headers_admin", "headers_accueil", "headers_tailleur"])
def test_tous_les_roles_peuvent_creer(client, request, headers):  # tableau des routes : « Tous »
    r = client.post(URL, json=FATOU, headers=request.getfixturevalue(headers))
    assert r.status_code == 201


def test_sans_jeton_401(client):
    assert client.post(URL, json=FATOU).status_code == 401
    assert client.get(URL).status_code == 401


# Route 8 : GET /clients
@pytest.fixture()
def plusieurs(client, headers_accueil):
    for nom, prenom, tel, genre in [
        ("Sow", "Moussa", "770000001", "homme"),
        ("Diop", "Fatou", "770000002", "femme"),
        ("Diop", "Awa", "780000003", "femme"),
        ("Ba", "Ali", "760000004", "enfant"),
    ]:
        r = client.post(URL, json={"nom": nom, "prenom": prenom, "telephone": tel, "genre": genre},
                        headers=headers_accueil)
        assert r.status_code == 201


def noms(r):
    return [(c["nom"], c["prenom"]) for c in r.json()["items"]]


def test_liste_triee_par_nom_puis_prenom(client, headers_tailleur, plusieurs):
    r = client.get(URL, headers=headers_tailleur)
    assert r.status_code == 200
    assert noms(r) == [("Ba", "Ali"), ("Diop", "Awa"), ("Diop", "Fatou"), ("Sow", "Moussa")]
    assert {k: r.json()[k] for k in ("total", "limit", "offset")} == {"total": 4, "limit": 20, "offset": 0}


def test_liste_pagination(client, headers_accueil, plusieurs):
    r = client.get(URL, params={"limit": 2, "offset": 1}, headers=headers_accueil)
    assert noms(r) == [("Diop", "Awa"), ("Diop", "Fatou")]
    assert r.json()["total"] == 4


def test_recherche_q_nom_prenom_insensible_a_la_casse(client, headers_accueil, plusieurs):
    assert noms(client.get(URL, params={"q": "dio"}, headers=headers_accueil)) == [
        ("Diop", "Awa"), ("Diop", "Fatou")]
    assert noms(client.get(URL, params={"q": "MOUS"}, headers=headers_accueil)) == [("Sow", "Moussa")]


def test_recherche_q_telephone_avec_separateurs(client, headers_accueil, plusieurs):
    r = client.get(URL, params={"q": "78 00"}, headers=headers_accueil)
    assert noms(r) == [("Diop", "Awa")]
    assert r.json()["total"] == 1


def test_recherche_q_trop_courte_422(client, headers_accueil):
    r = client.get(URL, params={"q": "d"}, headers=headers_accueil)
    assert r.status_code == 422


def test_filtre_genre_et_q(client, headers_accueil, plusieurs):
    assert noms(client.get(URL, params={"genre": "femme"}, headers=headers_accueil)) == [
        ("Diop", "Awa"), ("Diop", "Fatou")]
    assert noms(client.get(URL, params={"genre": "femme", "q": "fat"}, headers=headers_accueil)) == [
        ("Diop", "Fatou")]
    assert client.get(URL, params={"genre": "autre"}, headers=headers_accueil).status_code == 422


# Route 9 : GET /clients/{id}
def test_fiche_client(client, headers_tailleur, fatou):
    r = client.get(f"{URL}/{fatou['id']}", headers=headers_tailleur)
    assert r.status_code == 200
    assert r.json() == fatou


def test_fiche_client_inconnu_404(client, headers_accueil):
    r = client.get(f"{URL}/999", headers=headers_accueil)
    assert r.status_code == 404
    assert r.json() == {"detail": "Client 999 introuvable."}


# Route 10 : PATCH /clients/{id}
def test_modifier_ne_change_que_les_champs_envoyes(client, headers_accueil, fatou):
    r = client.patch(f"{URL}/{fatou['id']}", json={"adresse": "Médina, Dakar"}, headers=headers_accueil)
    assert r.status_code == 200
    corps = r.json()
    assert corps["adresse"] == "Médina, Dakar"
    assert (corps["nom"], corps["prenom"], corps["telephone"]) == ("Diop", "Fatou", "771234567")


def test_garder_son_propre_numero_n_est_pas_un_doublon(client, headers_accueil, fatou):
    r = client.patch(f"{URL}/{fatou['id']}", json={"telephone": "77.123.45.67"}, headers=headers_accueil)
    assert r.status_code == 200
    assert r.json()["telephone"] == "771234567"


def test_modifier_vers_numero_d_un_autre_409(client, headers_accueil, fatou):  # RG1
    autre = client.post(URL, json={**FATOU, "telephone": "781112233"}, headers=headers_accueil).json()
    r = client.patch(f"{URL}/{autre['id']}", json={"telephone": "77 123 45 67"}, headers=headers_accueil)
    assert r.status_code == 409


def test_modifier_telephone_invalide_422(client, headers_accueil, fatou):
    r = client.patch(f"{URL}/{fatou['id']}", json={"telephone": "abc"}, headers=headers_accueil)
    assert r.status_code == 422


@pytest.mark.parametrize("champ", ["nom", "prenom", "telephone"])
@pytest.mark.parametrize("valeur", [None, "", "   "])
def test_nom_prenom_telephone_ne_peuvent_pas_etre_vides(client, headers_accueil, fatou, champ, valeur):
    r = client.patch(f"{URL}/{fatou['id']}", json={champ: valeur}, headers=headers_accueil)
    assert r.status_code == 422
    assert champ in r.json()["detail"]


def test_champs_facultatifs_peuvent_etre_vides(client, headers_accueil, fatou):
    r = client.patch(f"{URL}/{fatou['id']}", json={"genre": None, "email": None}, headers=headers_accueil)
    assert r.status_code == 200
    assert r.json()["genre"] is None


def test_modifier_client_inconnu_404(client, headers_accueil):
    assert client.patch(f"{URL}/999", json={"nom": "X"}, headers=headers_accueil).status_code == 404


# Route 11 : DELETE /clients/{id}
def test_supprimer_client_204_supprime_aussi_ses_mesures(client, db, headers_admin, fatou, auteur):
    inserer_mesure(db, fatou["id"], auteur)
    r = client.delete(f"{URL}/{fatou['id']}", headers=headers_admin)
    assert r.status_code == 204
    assert r.content == b""
    assert db.get(Client, fatou["id"]) is None
    assert db.scalars(select(Mesure)).all() == []


def test_supprimer_client_avec_commandes_409(client, db, headers_admin, fatou, auteur):  # RG4
    inserer_commande(db, fatou["id"], auteur, "CMD-2026-00001", statut=Statut.annulee)
    r = client.delete(f"{URL}/{fatou['id']}", headers=headers_admin)
    assert r.status_code == 409
    assert r.json() == {"detail": f"Impossible de supprimer le client {fatou['id']} : il a 1 commande(s)."}
    assert db.get(Client, fatou["id"]) is not None


def test_supprimer_client_inconnu_404(client, headers_admin):
    assert client.delete(f"{URL}/999", headers=headers_admin).status_code == 404


@pytest.mark.parametrize("headers", ["headers_accueil", "headers_tailleur"])
def test_seul_l_admin_supprime_403(client, request, headers, fatou):
    r = client.delete(f"{URL}/{fatou['id']}", headers=request.getfixturevalue(headers))
    assert r.status_code == 403


# Route 12 : GET /clients/{id}/commandes
def test_commandes_du_client_plus_recente_d_abord(client, db, headers_tailleur, fatou, auteur):
    inserer_commande(db, fatou["id"], auteur, "CMD-2026-00001", jour=date(2026, 1, 5))
    inserer_commande(db, fatou["id"], auteur, "CMD-2026-00002", jour=date(2026, 3, 1),
                     total=30_000, paye=10_000)
    inserer_commande(db, fatou["id"], auteur, "CMD-2026-00003", jour=date(2026, 2, 1))
    autre = client.post(URL, json={**FATOU, "telephone": "780000000"}, headers=headers_tailleur).json()
    inserer_commande(db, autre["id"], auteur, "CMD-2026-00004")

    r = client.get(f"{URL}/{fatou['id']}/commandes", headers=headers_tailleur)
    assert r.status_code == 200
    corps = r.json()
    assert [c["numero"] for c in corps["items"]] == ["CMD-2026-00002", "CMD-2026-00003", "CMD-2026-00001"]
    assert corps["total"] == 3
    assert corps["items"][0]["solde"] == 20_000
    assert corps["items"][0]["statut"] == "en_attente"


def test_commandes_du_client_paginees(client, db, headers_accueil, fatou, auteur):
    for i in range(1, 4):
        inserer_commande(db, fatou["id"], auteur, f"CMD-2026-0000{i}", jour=date(2026, 1, i))
    r = client.get(f"{URL}/{fatou['id']}/commandes", params={"limit": 1, "offset": 1}, headers=headers_accueil)
    assert [c["numero"] for c in r.json()["items"]] == ["CMD-2026-00002"]
    assert (r.json()["total"], r.json()["limit"], r.json()["offset"]) == (3, 1, 1)


def test_commandes_client_inconnu_404(client, headers_accueil):
    assert client.get(f"{URL}/999/commandes", headers=headers_accueil).status_code == 404


# Route 13 : GET /clients/{id}/resume
def test_resume_client_sans_commande(client, headers_accueil, fatou):
    r = client.get(f"{URL}/{fatou['id']}/resume", headers=headers_accueil)
    assert r.status_code == 200
    assert r.json() == {
        "nb_commandes": 0, "chiffre_affaires": 0, "total_paye": 0,
        "solde_du": 0, "derniere_commande": None, "a_des_mesures": False,
    }


def test_resume_exclut_les_commandes_annulees(client, db, headers_tailleur, fatou, auteur):
    inserer_mesure(db, fatou["id"], auteur)
    inserer_commande(db, fatou["id"], auteur, "CMD-2026-00001", total=50_000, paye=20_000,
                     jour=date(2026, 2, 1))
    inserer_commande(db, fatou["id"], auteur, "CMD-2026-00002", statut=Statut.livree,
                     total=30_000, paye=30_000, jour=date(2026, 1, 1))
    inserer_commande(db, fatou["id"], auteur, "CMD-2026-00003", statut=Statut.annulee,
                     total=99_000, paye=5_000, jour=date(2026, 6, 1))

    r = client.get(f"{URL}/{fatou['id']}/resume", headers=headers_tailleur)
    assert r.status_code == 200
    assert r.json() == {
        "nb_commandes": 2, "chiffre_affaires": 80_000, "total_paye": 50_000,
        "solde_du": 30_000, "derniere_commande": "2026-02-01", "a_des_mesures": True,
    }


def test_resume_client_inconnu_404(client, headers_accueil):
    assert client.get(f"{URL}/999/resume", headers=headers_accueil).status_code == 404
