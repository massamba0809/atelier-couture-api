"""Routes 24 à 26 : création, liste, détail des commandes. RG5 à RG9, RG11, RG15 (annexe A, étape 3)."""
from datetime import date, timedelta

import pytest

from app.models.commande import Commande
from app.models.enums import Statut

URL = "/api/v1/commandes"
AUJ = date.today()


@pytest.fixture()
def prestations(client, headers_admin) -> dict:
    """Boubou (35 000, 10 j), Pantalon (12 000, 4 j), Retouche retirée du catalogue. {nom: id}."""
    ids = {}
    for nom, prix, delai in [("Boubou", 35_000, 10), ("Pantalon", 12_000, 4), ("Retouche", 3_000, 2)]:
        r = client.post("/api/v1/catalogue", json={"nom": nom, "prix_base": prix, "delai_jours": delai},
                        headers=headers_admin)
        ids[nom] = r.json()["id"]
    client.patch(f"/api/v1/catalogue/{ids['Retouche']}", json={"actif": False}, headers=headers_admin)
    return ids


def creer_client(client, headers, prenom="Fatou", nom="Diop", telephone="771234567") -> dict:
    r = client.post("/api/v1/clients", json={"nom": nom, "prenom": prenom, "telephone": telephone},
                    headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def fatou(client, headers_accueil) -> dict:
    return creer_client(client, headers_accueil)


def prendre_mesures(client, headers_tailleur, client_id, jour=None) -> dict:
    corps = {"tour_cou": 38} | ({"date_prise": jour.isoformat()} if jour else {})
    r = client.post(f"/api/v1/clients/{client_id}/mesures", json=corps, headers=headers_tailleur)
    assert r.status_code == 201, r.text
    return r.json()


def corps_commande(fatou, prestations, **autres) -> dict:
    """Annexe A, étape 3 : 2 boubous et 1 pantalon à prix négocié, avec une remise."""
    return {
        "client_id": fatou["id"],
        "lignes": [
            {"type_vetement_id": prestations["Boubou"], "quantite": 2},
            {"type_vetement_id": prestations["Pantalon"], "prix_unitaire": 10_000, "description": "lin"},
        ],
        "remise": 5_000,
        **autres,
    }


# --- Route 24 : POST /commandes -----------------------------------------------


def test_creer_commande_annexe_a_etape_3(client, db, headers_accueil, headers_tailleur, fatou, prestations):
    mesure = prendre_mesures(client, headers_tailleur, fatou["id"])
    r = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil)
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["numero"] == f"CMD-{AUJ.year}-{c['id']:05d}"                       # RG5
    assert c["statut"] == "en_attente"
    assert [(lg["type_vetement_nom"], lg["quantite"], lg["prix_unitaire"], lg["sous_total"])
            for lg in c["lignes"]] == [("Boubou", 2, 35_000, 70_000), ("Pantalon", 1, 10_000, 10_000)]  # RG6
    assert (c["montant_total"], c["montant_paye"], c["solde"]) == (75_000, 0, 75_000)  # RG7
    assert c["date_commande"] == AUJ.isoformat()
    assert c["date_livraison_prevue"] == (AUJ + timedelta(days=10)).isoformat()  # RG8 : plus long délai
    assert c["mesure_id"] == mesure["id"]                                           # RG9 : automatique
    assert c["client_nom"] == "Fatou Diop" and c["en_retard"] is False
    assert c["paiements"] == [] and c["livraison"] is None

    historique = db.get(Commande, c["id"]).historique                               # RG15
    assert [(h.ancien_statut, h.nouveau_statut) for h in historique] == [(None, Statut.en_attente)]


def test_numeros_successifs_uniques(client, headers_accueil, fatou, prestations):
    n1 = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil).json()["numero"]
    n2 = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil).json()["numero"]
    assert n1 != n2 and n1.startswith(f"CMD-{AUJ.year}-") and len(n2) == len("CMD-2026-00002")


def test_rattache_les_dernieres_mesures(client, headers_accueil, headers_tailleur, fatou, prestations):  # RG9
    prendre_mesures(client, headers_tailleur, fatou["id"], jour=AUJ - timedelta(days=30))
    recente = prendre_mesures(client, headers_tailleur, fatou["id"], jour=AUJ - timedelta(days=2))
    prendre_mesures(client, headers_tailleur, fatou["id"], jour=AUJ - timedelta(days=60))
    r = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil)
    assert r.json()["mesure_id"] == recente["id"]


def test_sans_mesures_mesure_id_vide(client, headers_accueil, fatou, prestations):  # RG9
    assert client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil).json()["mesure_id"] is None


def test_mesures_choisies_explicitement(client, headers_accueil, headers_tailleur, fatou, prestations):
    ancienne = prendre_mesures(client, headers_tailleur, fatou["id"], jour=AUJ - timedelta(days=30))
    prendre_mesures(client, headers_tailleur, fatou["id"])
    r = client.post(URL, json=corps_commande(fatou, prestations, mesure_id=ancienne["id"]), headers=headers_accueil)
    assert r.json()["mesure_id"] == ancienne["id"]


def test_mesures_d_un_autre_client_422(client, headers_accueil, headers_tailleur, fatou, prestations):  # RG9
    awa = creer_client(client, headers_accueil, prenom="Awa", telephone="781112233")
    mesure_awa = prendre_mesures(client, headers_tailleur, awa["id"])
    r = client.post(URL, json=corps_commande(fatou, prestations, mesure_id=mesure_awa["id"]), headers=headers_accueil)
    assert r.status_code == 422
    assert r.json() == {"detail": f"La prise de mesures {mesure_awa['id']} n'appartient pas au client {fatou['id']}."}


def test_mesures_inexistantes_422(client, headers_accueil, fatou, prestations):  # RG9
    r = client.post(URL, json=corps_commande(fatou, prestations, mesure_id=999), headers=headers_accueil)
    assert r.status_code == 422


def test_prestation_retiree_422(client, headers_accueil, fatou, prestations):  # RG6
    corps = corps_commande(fatou, prestations)
    corps["lignes"].append({"type_vetement_id": prestations["Retouche"]})
    r = client.post(URL, json=corps, headers=headers_accueil)
    assert r.status_code == 422
    assert "Retouche" in r.json()["detail"]


def test_prestation_inconnue_404(client, headers_accueil, fatou):
    r = client.post(URL, json={"client_id": fatou["id"], "lignes": [{"type_vetement_id": 999}]},
                    headers=headers_accueil)
    assert r.status_code == 404


def test_client_inconnu_404(client, headers_accueil, prestations):
    r = client.post(URL, json={"client_id": 999, "lignes": [{"type_vetement_id": prestations["Boubou"]}]},
                    headers=headers_accueil)
    assert r.status_code == 404
    assert r.json() == {"detail": "Client 999 introuvable."}


def test_remise_superieure_aux_prestations_422(client, headers_accueil, fatou, prestations):  # RG7
    r = client.post(URL, json=corps_commande(fatou, prestations, remise=80_001), headers=headers_accueil)
    assert r.status_code == 422
    assert "remise" in r.json()["detail"]


def test_date_prevue_avant_la_commande_422(client, headers_accueil, fatou, prestations):  # RG8
    hier = (AUJ - timedelta(days=1)).isoformat()
    r = client.post(URL, json=corps_commande(fatou, prestations, date_livraison_prevue=hier), headers=headers_accueil)
    assert r.status_code == 422
    assert "précéder" in r.json()["detail"]


def test_date_prevue_choisie_acceptee(client, headers_accueil, fatou, prestations):
    jour = (AUJ + timedelta(days=3)).isoformat()
    r = client.post(URL, json=corps_commande(fatou, prestations, date_livraison_prevue=jour), headers=headers_accueil)
    assert r.json()["date_livraison_prevue"] == jour


@pytest.mark.parametrize("modif, champ", [
    ({"lignes": []}, "lignes"),
    ({"remise": -1}, "remise"),
    ({"lignes": [{"type_vetement_id": 1, "quantite": 0}]}, "quantite"),
    ({"lignes": [{"type_vetement_id": 1, "prix_unitaire": -5}]}, "prix_unitaire"),
])
def test_corps_invalide_422(client, headers_accueil, fatou, prestations, modif, champ):
    r = client.post(URL, json={**corps_commande(fatou, prestations), **modif}, headers=headers_accueil)
    assert r.status_code == 422
    assert champ in r.json()["detail"]


def test_un_refus_ne_laisse_aucune_trace(client, db, headers_accueil, fatou, prestations):
    client.post(URL, json=corps_commande(fatou, prestations, remise=999_999), headers=headers_accueil)
    db.rollback()
    assert db.query(Commande).count() == 0


def test_tailleur_ne_peut_pas_creer_403(client, headers_tailleur, fatou, prestations):
    assert client.post(URL, json=corps_commande(fatou, prestations), headers=headers_tailleur).status_code == 403


def test_admin_peut_creer(client, headers_admin, fatou, prestations):
    assert client.post(URL, json=corps_commande(fatou, prestations), headers=headers_admin).status_code == 201


def test_sans_jeton_401(client):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={}).status_code == 401


# --- Route 25 : GET /commandes ------------------------------------------------


@pytest.fixture()
def trois_commandes(client, db, headers_accueil, fatou, prestations) -> list[dict]:
    """Fatou : 2 commandes (dont 1 en retard) ; Awa : 1 commande annulée en retard. Dates de commande distinctes."""
    awa = creer_client(client, headers_accueil, prenom="Awa", nom="Ndiaye", telephone="781112233")
    cmds = [client.post(URL, json=corps_commande(c, prestations), headers=headers_accueil).json()
            for c in (fatou, fatou, awa)]
    reglages = [  # (date_commande, date_livraison_prevue, statut)
        (AUJ - timedelta(days=20), AUJ - timedelta(days=5), Statut.en_couture),  # en retard
        (AUJ - timedelta(days=2), AUJ + timedelta(days=8), Statut.en_attente),
        (AUJ - timedelta(days=10), AUJ - timedelta(days=1), Statut.annulee),     # annulée : jamais en retard
    ]
    for cmd, (jour, prevue, statut) in zip(cmds, reglages):
        objet = db.get(Commande, cmd["id"])
        objet.date_commande, objet.date_livraison_prevue, objet.statut = jour, prevue, statut
    db.commit()
    return cmds


def numeros(r):
    return [c["numero"] for c in r.json()["items"]]


def test_liste_plus_recente_d_abord_avec_champs_calcules(client, headers_tailleur, trois_commandes):
    r = client.get(URL, headers=headers_tailleur)
    assert r.status_code == 200
    c0, c1, c2 = trois_commandes
    assert numeros(r) == [c1["numero"], c2["numero"], c0["numero"]]
    assert {k: r.json()[k] for k in ("total", "limit", "offset")} == {"total": 3, "limit": 20, "offset": 0}
    premier = r.json()["items"][0]
    assert (premier["client_nom"], premier["solde"], premier["en_retard"]) == ("Fatou Diop", 75_000, False)


def test_filtre_en_retard(client, headers_accueil, trois_commandes):  # RG11
    c0, c1, c2 = trois_commandes
    r = client.get(URL, params={"en_retard": "true"}, headers=headers_accueil)
    assert numeros(r) == [c0["numero"]]
    assert r.json()["items"][0]["en_retard"] is True
    assert numeros(client.get(URL, params={"en_retard": "false"}, headers=headers_accueil)) == [
        c1["numero"], c2["numero"]]


def test_filtres_statut_client_numero(client, headers_accueil, fatou, trois_commandes):
    c0, c1, c2 = trois_commandes
    assert numeros(client.get(URL, params={"statut": "annulee"}, headers=headers_accueil)) == [c2["numero"]]
    assert numeros(client.get(URL, params={"client_id": fatou["id"]}, headers=headers_accueil)) == [
        c1["numero"], c0["numero"]]
    assert numeros(client.get(URL, params={"numero": c0["numero"][-5:]}, headers=headers_accueil)) == [c0["numero"]]


def test_filtre_dates_de_commande(client, headers_accueil, trois_commandes):
    c0, c1, c2 = trois_commandes
    params = {"date_min": (AUJ - timedelta(days=15)).isoformat(), "date_max": (AUJ - timedelta(days=2)).isoformat()}
    assert numeros(client.get(URL, params=params, headers=headers_accueil)) == [c1["numero"], c2["numero"]]


def test_liste_paginee(client, headers_accueil, trois_commandes):
    r = client.get(URL, params={"limit": 1, "offset": 1}, headers=headers_accueil)
    assert numeros(r) == [trois_commandes[2]["numero"]]
    assert r.json()["total"] == 3


def test_filtre_statut_invalide_422(client, headers_accueil):
    assert client.get(URL, params={"statut": "perdue"}, headers=headers_accueil).status_code == 422


# --- Route 26 : GET /commandes/{id} -------------------------------------------


def test_detail_avec_paiements(client, headers_accueil, headers_tailleur, fatou, prestations):
    cree = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil).json()
    client.post(f"{URL}/{cree['id']}/paiements", json={"montant": 20_000, "mode": "wave"}, headers=headers_accueil)

    r = client.get(f"{URL}/{cree['id']}", headers=headers_tailleur)
    assert r.status_code == 200
    d = r.json()
    assert (d["montant_paye"], d["solde"]) == (20_000, 55_000)
    assert [(p["montant"], p["mode"]) for p in d["paiements"]] == [(20_000, "wave")]
    assert d["lignes"] == cree["lignes"]
    assert d["livraison"] is None


def test_detail_en_retard(client, db, headers_accueil, fatou, prestations):  # RG11
    cree = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil).json()
    db.get(Commande, cree["id"]).date_livraison_prevue = AUJ - timedelta(days=1)
    db.commit()
    assert client.get(f"{URL}/{cree['id']}", headers=headers_accueil).json()["en_retard"] is True


def test_detail_inconnu_404(client, headers_accueil):
    r = client.get(f"{URL}/999", headers=headers_accueil)
    assert r.status_code == 404
    assert r.json() == {"detail": "Commande 999 introuvable."}
