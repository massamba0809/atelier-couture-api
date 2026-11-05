"""Routes 18 à 23 par HTTP : codes de retour et droits par rôle (annexe A, étape 2)."""
from datetime import date

import pytest

from app.models.commande import Commande

URL_CLIENTS = "/api/v1/clients"
URL_MESURES = "/api/v1/mesures"


@pytest.fixture()
def fatou(client, headers_accueil) -> dict:
    r = client.post(
        URL_CLIENTS,
        json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67"},
        headers=headers_accueil,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def mesure(client, headers_tailleur, fatou) -> dict:
    r = client.post(
        f"{URL_CLIENTS}/{fatou['id']}/mesures",
        json={"tour_cou": 38, "tour_taille": 80},
        headers=headers_tailleur,
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- Route 18 : POST /clients/{id}/mesures ------------------------------------


def test_tailleur_prend_les_mesures_201(client, headers_tailleur, fatou):  # annexe A, étape 2
    r = client.post(
        f"{URL_CLIENTS}/{fatou['id']}/mesures", json={"tour_cou": 38}, headers=headers_tailleur
    )
    assert r.status_code == 201
    corps = r.json()
    assert corps["client_id"] == fatou["id"]
    assert corps["tour_cou"] == 38
    assert corps["date_prise"] == date.today().isoformat()


def test_accueil_ne_peut_pas_prendre_de_mesures_403(client, headers_accueil, fatou):  # annexe A
    r = client.post(
        f"{URL_CLIENTS}/{fatou['id']}/mesures", json={"tour_cou": 38}, headers=headers_accueil
    )
    assert r.status_code == 403


def test_admin_peut_prendre_des_mesures(client, headers_admin, fatou):  # l'admin peut tout faire
    r = client.post(
        f"{URL_CLIENTS}/{fatou['id']}/mesures", json={"tour_cou": 38}, headers=headers_admin
    )
    assert r.status_code == 201


def test_sans_jeton_401(client, fatou):
    r = client.post(f"{URL_CLIENTS}/{fatou['id']}/mesures", json={"tour_cou": 38})
    assert r.status_code == 401


def test_prise_sans_aucune_mesure_422(client, headers_tailleur, fatou):  # RG2
    r = client.post(
        f"{URL_CLIENTS}/{fatou['id']}/mesures", json={"notes": "rien"}, headers=headers_tailleur
    )
    assert r.status_code == 422
    assert "au moins une mesure" in r.json()["detail"]


def test_mesure_superieure_a_300_422(client, headers_tailleur, fatou):  # RG2
    r = client.post(
        f"{URL_CLIENTS}/{fatou['id']}/mesures", json={"taille_cm": 301}, headers=headers_tailleur
    )
    assert r.status_code == 422
    assert "taille_cm" in r.json()["detail"]


def test_prise_pour_client_inconnu_404(client, headers_tailleur):
    r = client.post(f"{URL_CLIENTS}/999/mesures", json={"tour_cou": 38}, headers=headers_tailleur)
    assert r.status_code == 404


# --- Routes 19 à 21 : lecture (tous les rôles) --------------------------------


def test_accueil_lit_l_historique(client, headers_accueil, fatou, mesure):  # route 19
    r = client.get(f"{URL_CLIENTS}/{fatou['id']}/mesures", headers=headers_accueil)
    assert r.status_code == 200
    assert [m["id"] for m in r.json()] == [mesure["id"]]


def test_derniere_mesure(client, headers_accueil, fatou, mesure):  # route 20
    r = client.get(f"{URL_CLIENTS}/{fatou['id']}/mesures/derniere", headers=headers_accueil)
    assert r.status_code == 200
    assert r.json()["id"] == mesure["id"]


def test_derniere_mesure_404_si_aucune(client, headers_accueil, fatou):  # route 20
    r = client.get(f"{URL_CLIENTS}/{fatou['id']}/mesures/derniere", headers=headers_accueil)
    assert r.status_code == 404
    assert "aucune prise de mesures" in r.json()["detail"]


def test_obtenir_une_mesure(client, headers_accueil, mesure):  # route 21
    r = client.get(f"{URL_MESURES}/{mesure['id']}", headers=headers_accueil)
    assert r.status_code == 200
    assert r.json()["tour_taille"] == 80


# --- Route 22 : PATCH /mesures/{id} -------------------------------------------


def test_tailleur_corrige_une_mesure(client, headers_tailleur, mesure):
    r = client.patch(f"{URL_MESURES}/{mesure['id']}", json={"tour_cou": 39}, headers=headers_tailleur)
    assert r.status_code == 200
    assert r.json()["tour_cou"] == 39
    assert r.json()["tour_taille"] == 80


def test_correction_qui_efface_tout_422(client, headers_tailleur, mesure):  # route 22, RG2
    r = client.patch(
        f"{URL_MESURES}/{mesure['id']}",
        json={"tour_cou": None, "tour_taille": None},
        headers=headers_tailleur,
    )
    assert r.status_code == 422


def test_accueil_ne_peut_pas_corriger_403(client, headers_accueil, mesure):
    r = client.patch(f"{URL_MESURES}/{mesure['id']}", json={"tour_cou": 39}, headers=headers_accueil)
    assert r.status_code == 403


# --- Route 23 : DELETE /mesures/{id} ------------------------------------------


def test_tailleur_supprime_une_mesure_204(client, headers_tailleur, mesure):
    r = client.delete(f"{URL_MESURES}/{mesure['id']}", headers=headers_tailleur)
    assert r.status_code == 204
    assert client.get(f"{URL_MESURES}/{mesure['id']}", headers=headers_tailleur).status_code == 404


def test_suppression_mesure_utilisee_409(client, db, headers_tailleur, fatou, mesure):  # RG4
    db.add(Commande(
        numero="CMD-2026-00001", client_id=fatou["id"], mesure_id=mesure["id"],
        date_livraison_prevue=date(2026, 1, 15), cree_par_id=mesure["prise_par_id"],
    ))
    db.commit()
    r = client.delete(f"{URL_MESURES}/{mesure['id']}", headers=headers_tailleur)
    assert r.status_code == 409


def test_accueil_ne_peut_pas_supprimer_403(client, headers_accueil, mesure):
    r = client.delete(f"{URL_MESURES}/{mesure['id']}", headers=headers_accueil)
    assert r.status_code == 403
