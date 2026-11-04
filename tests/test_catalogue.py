"""Routes 14 à 17 : catalogue des prestations. Nom unique, actifs_seulement, droits par rôle."""
from datetime import date

import pytest

from app.models.client import Client
from app.models.commande import Commande, LigneCommande
from app.models.enums import Role
from tests.conftest import creer_utilisateur

URL = "/api/v1/catalogue"
BOUBOU = {"nom": "Boubou", "description": "Boubou homme en bazin ou brodé", "prix_base": 35_000, "delai_jours": 10}


@pytest.fixture()
def boubou(client, headers_admin) -> dict:
    r = client.post(URL, json=BOUBOU, headers=headers_admin)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def catalogue(client, headers_admin) -> dict:
    """Robe et Chemise actives, Retouche retirée. Renvoie {nom: id}."""
    ids = {}
    for nom, prix, delai in [("Robe", 30_000, 7), ("Retouche", 3_000, 2), ("Chemise", 15_000, 5)]:
        r = client.post(URL, json={"nom": nom, "prix_base": prix, "delai_jours": delai}, headers=headers_admin)
        ids[nom] = r.json()["id"]
    client.patch(f"{URL}/{ids['Retouche']}", json={"actif": False}, headers=headers_admin)
    return ids


# Route 14 : POST /catalogue
def test_creer_prestation_201(client, headers_admin):
    r = client.post(URL, json=BOUBOU, headers=headers_admin)
    assert r.status_code == 201
    corps = r.json()
    assert {k: corps[k] for k in BOUBOU} == BOUBOU
    assert corps["actif"] is True
    assert "id" in corps


def test_nom_existant_409(client, headers_admin, boubou):
    r = client.post(URL, json=BOUBOU, headers=headers_admin)
    assert r.status_code == 409
    assert r.json() == {"detail": "Une prestation existe déjà avec le nom « Boubou »."}


def test_nom_existant_409_meme_avec_majuscules_et_espaces(client, headers_admin, boubou):
    r = client.post(URL, json={**BOUBOU, "nom": "  BOUBOU "}, headers=headers_admin)
    assert r.status_code == 409


@pytest.mark.parametrize("champ, valeur", [("prix_base", -1), ("delai_jours", -1), ("nom", "  "),
                                           ("prix_base", "cher")])
def test_creer_prestation_invalide_422(client, headers_admin, champ, valeur):
    r = client.post(URL, json={**BOUBOU, champ: valeur}, headers=headers_admin)
    assert r.status_code == 422
    assert champ in r.json()["detail"]


def test_creer_prestation_champ_manquant_422(client, headers_admin):
    r = client.post(URL, json={"nom": "Boubou", "prix_base": 35_000}, headers=headers_admin)
    assert r.status_code == 422
    assert "delai_jours : champ obligatoire" in r.json()["detail"]


@pytest.mark.parametrize("headers", ["headers_accueil", "headers_tailleur"])
def test_seul_l_admin_cree_403(client, request, headers):
    r = client.post(URL, json=BOUBOU, headers=request.getfixturevalue(headers))
    assert r.status_code == 403


def test_sans_jeton_401(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=BOUBOU).status_code == 401


# Route 15 : GET /catalogue
@pytest.mark.parametrize("headers", ["headers_admin", "headers_accueil", "headers_tailleur"])
def test_liste_actives_triee_par_nom(client, request, catalogue, headers):
    r = client.get(URL, headers=request.getfixturevalue(headers))
    assert r.status_code == 200
    assert [p["nom"] for p in r.json()] == ["Chemise", "Robe"]


def test_liste_actifs_seulement_false_inclut_les_retirees(client, headers_accueil, catalogue):
    r = client.get(URL, params={"actifs_seulement": "false"}, headers=headers_accueil)
    assert r.status_code == 200
    assert [(p["nom"], p["actif"]) for p in r.json()] == [
        ("Chemise", True), ("Retouche", False), ("Robe", True)]


# Route 16 : GET /catalogue/{id}
def test_detail_prestation(client, headers_tailleur, boubou):
    r = client.get(f"{URL}/{boubou['id']}", headers=headers_tailleur)
    assert r.status_code == 200
    assert r.json() == boubou


def test_detail_prestation_retiree_reste_consultable(client, headers_accueil, catalogue):
    r = client.get(f"{URL}/{catalogue['Retouche']}", headers=headers_accueil)
    assert r.status_code == 200
    assert r.json()["actif"] is False


def test_detail_prestation_inconnue_404(client, headers_accueil):
    r = client.get(f"{URL}/999", headers=headers_accueil)
    assert r.status_code == 404
    assert r.json() == {"detail": "Prestation 999 introuvable."}


# Route 17 : PATCH /catalogue/{id}
def test_modifier_ne_change_que_les_champs_envoyes(client, headers_admin, boubou):
    r = client.patch(f"{URL}/{boubou['id']}", json={"prix_base": 40_000}, headers=headers_admin)
    assert r.status_code == 200
    assert r.json() == {**boubou, "prix_base": 40_000}


def test_modifier_nom_et_delai(client, headers_admin, boubou):
    r = client.patch(f"{URL}/{boubou['id']}", json={"nom": "Grand boubou", "delai_jours": 12},
                     headers=headers_admin)
    assert r.status_code == 200
    assert (r.json()["nom"], r.json()["delai_jours"]) == ("Grand boubou", 12)


def test_garder_son_propre_nom_n_est_pas_un_doublon(client, headers_admin, boubou):
    r = client.patch(f"{URL}/{boubou['id']}", json={"nom": "boubou"}, headers=headers_admin)
    assert r.status_code == 200


def test_renommer_vers_un_nom_existant_409(client, headers_admin, boubou, catalogue):
    r = client.patch(f"{URL}/{catalogue['Robe']}", json={"nom": "Boubou"}, headers=headers_admin)
    assert r.status_code == 409


@pytest.mark.parametrize("champ", ["nom", "prix_base", "delai_jours", "actif"])
def test_champs_obligatoires_ne_peuvent_pas_etre_vides(client, headers_admin, boubou, champ):
    r = client.patch(f"{URL}/{boubou['id']}", json={champ: None}, headers=headers_admin)
    assert r.status_code == 422
    assert champ in r.json()["detail"]


def test_modifier_prestation_inconnue_404(client, headers_admin):
    assert client.patch(f"{URL}/999", json={"prix_base": 1}, headers=headers_admin).status_code == 404


@pytest.mark.parametrize("headers", ["headers_accueil", "headers_tailleur"])
def test_seul_l_admin_modifie_403(client, request, headers, boubou):
    r = client.patch(f"{URL}/{boubou['id']}", json={"prix_base": 1}, headers=request.getfixturevalue(headers))
    assert r.status_code == 403


def test_retirer_ou_changer_le_prix_ne_touche_pas_aux_anciennes_commandes(client, db, headers_admin, boubou):
    auteur = creer_utilisateur(db, Role.accueil, email="auteur@atelier.sn")
    cliente = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    db.add(cliente)
    db.flush()
    commande = Commande(numero="CMD-2026-00001", client_id=cliente.id, date_commande=date(2026, 1, 10),
                        date_livraison_prevue=date(2026, 1, 20), montant_total=35_000, cree_par_id=auteur.id)
    commande.lignes.append(LigneCommande(type_vetement_id=boubou["id"], quantite=1, prix_unitaire=35_000))
    db.add(commande)
    db.commit()

    r = client.patch(f"{URL}/{boubou['id']}", json={"actif": False, "prix_base": 50_000}, headers=headers_admin)
    assert r.status_code == 200
    assert r.json()["actif"] is False

    db.refresh(commande)
    assert [(lg.type_vetement_id, lg.prix_unitaire) for lg in commande.lignes] == [(boubou["id"], 35_000)]
    assert commande.montant_total == 35_000
    assert [p["nom"] for p in client.get(URL, headers=headers_admin).json()] == []
