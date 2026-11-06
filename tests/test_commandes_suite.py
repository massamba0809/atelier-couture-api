"""Routes 27 à 31 : modification, statut, historique, lignes. RG7 à RG10, RG12 à RG15 (annexe A, étapes 4 et 5)."""
from datetime import date, timedelta

import pytest

from app.models.commande import Commande
from app.models.enums import Statut
from tests.test_commandes import (  # noqa: F401  (fixtures réutilisées)
    corps_commande,
    creer_client,
    fatou,
    prendre_mesures,
    prestations,
)

URL = "/api/v1/commandes"
AUJ = date.today()


@pytest.fixture()
def commande(client, headers_accueil, fatou, prestations) -> dict:  # noqa: F811
    """2 boubous (70 000) + 1 pantalon à 10 000, remise 5 000 → total 75 000. Statut en_attente."""
    r = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil)
    assert r.status_code == 201, r.text
    return r.json()


def payer(client, commande, headers, montant):
    r = client.post(f"{URL}/{commande['id']}/paiements", json={"montant": montant, "mode": "wave"}, headers=headers)
    assert r.status_code == 201, r.text


def forcer_statut(db, commande, statut):
    db.get(Commande, commande["id"]).statut = statut
    db.commit()


def statut(client, commande, headers, nouveau, commentaire=None):
    corps = {"statut": nouveau} | ({"commentaire": commentaire} if commentaire is not None else {})
    return client.post(f"{URL}/{commande['id']}/statut", json=corps, headers=headers)


# --- Route 27 : PATCH /commandes/{id} -----------------------------------------


def test_modifier_notes_et_date_seulement(client, headers_accueil, commande):
    jour = (AUJ + timedelta(days=20)).isoformat()
    r = client.patch(f"{URL}/{commande['id']}", json={"notes": "urgent", "date_livraison_prevue": jour},
                     headers=headers_accueil)
    assert r.status_code == 200
    c = r.json()
    assert (c["notes"], c["date_livraison_prevue"]) == ("urgent", jour)
    assert (c["remise"], c["montant_total"]) == (5_000, 75_000)  # non envoyés : inchangés


def test_modifier_remise_recalcule_les_montants(client, headers_accueil, commande):  # RG7
    r = client.patch(f"{URL}/{commande['id']}", json={"remise": 10_000}, headers=headers_accueil)
    assert (r.json()["montant_total"], r.json()["solde"]) == (70_000, 70_000)


def test_remise_superieure_aux_prestations_422(client, db, headers_accueil, commande):  # RG7
    r = client.patch(f"{URL}/{commande['id']}", json={"remise": 80_001}, headers=headers_accueil)
    assert r.status_code == 422
    db.expire_all()
    assert db.get(Commande, commande["id"]).remise == 5_000


def test_remise_ramenant_le_total_sous_le_paye_409(client, headers_accueil, commande):  # RG7
    payer(client, commande, headers_accueil, 70_000)
    r = client.patch(f"{URL}/{commande['id']}", json={"remise": 20_000}, headers=headers_accueil)
    assert r.status_code == 409
    assert "déjà payé (70000 FCFA)" in r.json()["detail"]


def test_date_prevue_avant_la_commande_422(client, headers_accueil, commande):  # RG8
    hier = (AUJ - timedelta(days=1)).isoformat()
    r = client.patch(f"{URL}/{commande['id']}", json={"date_livraison_prevue": hier}, headers=headers_accueil)
    assert r.status_code == 422


def test_changer_les_mesures(client, headers_accueil, headers_tailleur, fatou, commande):  # noqa: F811
    mesure = prendre_mesures(client, headers_tailleur, fatou["id"])
    r = client.patch(f"{URL}/{commande['id']}", json={"mesure_id": mesure["id"]}, headers=headers_accueil)
    assert r.json()["mesure_id"] == mesure["id"]
    r = client.patch(f"{URL}/{commande['id']}", json={"mesure_id": None}, headers=headers_accueil)
    assert r.json()["mesure_id"] is None


def test_mesures_d_un_autre_client_422(client, headers_accueil, headers_tailleur, commande):  # RG9
    awa = creer_client(client, headers_accueil, prenom="Awa", telephone="781112233")
    mesure = prendre_mesures(client, headers_tailleur, awa["id"])
    r = client.patch(f"{URL}/{commande['id']}", json={"mesure_id": mesure["id"]}, headers=headers_accueil)
    assert r.status_code == 422


@pytest.mark.parametrize("champ", ["remise", "date_livraison_prevue"])
def test_champs_obligatoires_ne_peuvent_pas_etre_vides(client, headers_accueil, commande, champ):
    r = client.patch(f"{URL}/{commande['id']}", json={champ: None}, headers=headers_accueil)
    assert r.status_code == 422


@pytest.mark.parametrize("final", [Statut.livree, Statut.annulee])
def test_commande_livree_ou_annulee_non_modifiable_409(client, db, headers_accueil, commande, final):  # RG12
    forcer_statut(db, commande, final)
    r = client.patch(f"{URL}/{commande['id']}", json={"notes": "trop tard"}, headers=headers_accueil)
    assert r.status_code == 409
    assert r.json()["detail"] == f"La commande {commande['numero']} est « {final.value} » : elle n'est plus modifiable."


def test_modification_possible_en_cours_de_production(client, db, headers_accueil, commande):
    forcer_statut(db, commande, Statut.en_couture)
    assert client.patch(f"{URL}/{commande['id']}", json={"notes": "ok"}, headers=headers_accueil).status_code == 200


def test_tailleur_ne_peut_pas_modifier_403(client, headers_tailleur, commande):
    assert client.patch(f"{URL}/{commande['id']}", json={"notes": "x"}, headers=headers_tailleur).status_code == 403


def test_modifier_commande_inconnue_404(client, headers_accueil):
    assert client.patch(f"{URL}/999", json={"notes": "x"}, headers=headers_accueil).status_code == 404


# --- Route 28 : POST /commandes/{id}/statut -----------------------------------


def test_annexe_a_etape_4_transition_interdite(client, headers_accueil, commande):  # RG13
    r = statut(client, commande, headers_accueil, "terminee")
    assert r.status_code == 409
    assert r.json() == {"detail": "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe"}


def test_annexe_a_etape_5_parcours_tailleur_et_historique(client, headers_tailleur, commande):  # RG13, RG15
    parcours = ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]
    for s in parcours:
        r = statut(client, commande, headers_tailleur, s, commentaire="ok" if s == "retouches" else None)
        assert r.status_code == 200, (s, r.text)
        assert r.json()["statut"] == s

    r = client.get(f"{URL}/{commande['id']}/historique", headers=headers_tailleur)  # route 29
    assert r.status_code == 200
    lignes = r.json()
    attendus = list(zip([None, "en_attente", *parcours[:-1]], ["en_attente", *parcours]))
    assert [(h["ancien_statut"], h["nouveau_statut"]) for h in lignes] == attendus
    assert lignes[4]["commentaire"] == "ok"
    assert {"id", "utilisateur_id", "date_changement"} <= lignes[0].keys()


def test_meme_statut_409(client, headers_accueil, commande):  # RG13
    assert statut(client, commande, headers_accueil, "en_attente").status_code == 409


def test_livree_par_la_route_statut_409(client, db, headers_accueil, commande):  # RG13
    forcer_statut(db, commande, Statut.terminee)
    r = statut(client, commande, headers_accueil, "livree")
    assert r.status_code == 409
    assert "confirmation de livraison" in r.json()["detail"]


def test_tailleur_ne_peut_pas_annuler_403(client, headers_tailleur, commande):  # RG14
    r = statut(client, commande, headers_tailleur, "annulee", commentaire="client parti")
    assert r.status_code == 403
    assert r.json() == {"detail": "Le tailleur ne peut pas annuler une commande."}


def test_accueil_annule_sans_acompte_sans_commentaire(client, headers_accueil, commande):  # RG14
    r = statut(client, commande, headers_accueil, "annulee")
    assert r.status_code == 200
    assert r.json()["statut"] == "annulee"


@pytest.mark.parametrize("commentaire", [None, "", "   "])
def test_annuler_avec_acompte_exige_un_commentaire_422(client, headers_accueil, commande, commentaire):  # RG14
    payer(client, commande, headers_accueil, 20_000)
    r = statut(client, commande, headers_accueil, "annulee", commentaire=commentaire)
    assert r.status_code == 422
    assert "20000 FCFA" in r.json()["detail"]


def test_annuler_avec_acompte_et_commentaire(client, headers_accueil, commande):  # RG14, RG15
    payer(client, commande, headers_accueil, 20_000)
    r = statut(client, commande, headers_accueil, "annulee", commentaire="  avoir de 20 000 FCFA ")
    assert r.status_code == 200
    h = client.get(f"{URL}/{commande['id']}/historique", headers=headers_accueil).json()
    assert (h[-1]["nouveau_statut"], h[-1]["commentaire"]) == ("annulee", "avoir de 20 000 FCFA")


def test_statut_invalide_422(client, headers_accueil, commande):
    assert statut(client, commande, headers_accueil, "perdue").status_code == 422


def test_statut_commande_inconnue_404(client, headers_accueil):
    assert client.post(f"{URL}/999/statut", json={"statut": "en_coupe"}, headers=headers_accueil).status_code == 404


# --- Route 29 : GET /commandes/{id}/historique --------------------------------


def test_historique_a_la_creation(client, headers_tailleur, commande):
    r = client.get(f"{URL}/{commande['id']}/historique", headers=headers_tailleur)
    assert [(h["ancien_statut"], h["nouveau_statut"], h["commentaire"]) for h in r.json()] == [
        (None, "en_attente", None)]


def test_historique_commande_inconnue_404(client, headers_accueil):
    assert client.get(f"{URL}/999/historique", headers=headers_accueil).status_code == 404


# --- Route 30 : POST /commandes/{id}/lignes -----------------------------------


def test_ajouter_une_ligne_201_montants_recalcules(client, headers_accueil, commande, prestations):  # noqa: F811
    r = client.post(f"{URL}/{commande['id']}/lignes",
                    json={"type_vetement_id": prestations["Pantalon"], "quantite": 2}, headers=headers_accueil)
    assert r.status_code == 201
    c = r.json()
    assert c["lignes"][-1] | {"id": 0} == {
        "id": 0, "type_vetement_id": prestations["Pantalon"], "type_vetement_nom": "Pantalon",
        "description": None, "quantite": 2, "prix_unitaire": 12_000, "sous_total": 24_000}
    assert (c["montant_total"], c["solde"]) == (99_000, 99_000)
    assert c["date_livraison_prevue"] == commande["date_livraison_prevue"]  # inchangée


def test_ajouter_prestation_retiree_422(client, headers_accueil, commande, prestations):  # noqa: F811  RG6
    r = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": prestations["Retouche"]},
                    headers=headers_accueil)
    assert r.status_code == 422


def test_ajouter_ligne_hors_en_attente_409(client, db, headers_accueil, commande, prestations):  # noqa: F811  RG10
    forcer_statut(db, commande, Statut.en_coupe)
    r = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": prestations["Boubou"]},
                    headers=headers_accueil)
    assert r.status_code == 409
    assert "en_attente" in r.json()["detail"]


def test_ajouter_ligne_commande_annulee_409(client, db, headers_accueil, commande, prestations):  # noqa: F811  RG12
    forcer_statut(db, commande, Statut.annulee)
    r = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": prestations["Boubou"]},
                    headers=headers_accueil)
    assert r.status_code == 409
    assert "n'est plus modifiable" in r.json()["detail"]


def test_ajouter_prestation_inconnue_404(client, headers_accueil, commande):
    r = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": 999}, headers=headers_accueil)
    assert r.status_code == 404


def test_tailleur_ne_peut_pas_ajouter_de_ligne_403(client, headers_tailleur, commande, prestations):  # noqa: F811
    r = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": prestations["Boubou"]},
                    headers=headers_tailleur)
    assert r.status_code == 403


# --- Route 31 : DELETE /commandes/{id}/lignes/{ligne_id} ----------------------


def test_retirer_une_ligne(client, headers_accueil, commande):
    pantalon = commande["lignes"][1]
    r = client.delete(f"{URL}/{commande['id']}/lignes/{pantalon['id']}", headers=headers_accueil)
    assert r.status_code == 200
    c = r.json()
    assert [lg["type_vetement_nom"] for lg in c["lignes"]] == ["Boubou"]
    assert c["montant_total"] == 65_000


def test_retirer_la_derniere_ligne_409(client, headers_accueil, commande):  # RG10
    client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][1]['id']}", headers=headers_accueil)
    r = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][0]['id']}", headers=headers_accueil)
    assert r.status_code == 409
    assert "au moins une prestation" in r.json()["detail"]


def test_retirer_ligne_inconnue_ou_d_une_autre_commande_404(client, headers_accueil, fatou, prestations, commande):  # noqa: F811
    autre = client.post(URL, json=corps_commande(fatou, prestations), headers=headers_accueil).json()
    r = client.delete(f"{URL}/{commande['id']}/lignes/{autre['lignes'][0]['id']}", headers=headers_accueil)
    assert r.status_code == 404
    assert client.delete(f"{URL}/{commande['id']}/lignes/999", headers=headers_accueil).status_code == 404


def test_retirer_ligne_hors_en_attente_409(client, db, headers_accueil, commande):  # RG10
    forcer_statut(db, commande, Statut.essayage)
    r = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][1]['id']}", headers=headers_accueil)
    assert r.status_code == 409


def test_retirer_ligne_sous_le_paye_409_et_ligne_conservee(client, db, headers_accueil, commande):  # RG7
    payer(client, commande, headers_accueil, 70_000)  # retirer les boubous ramènerait le total à 5 000
    r = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][0]['id']}", headers=headers_accueil)
    assert r.status_code == 409
    db.expire_all()
    assert len(db.get(Commande, commande["id"]).lignes) == 2


def test_retirer_ligne_remise_superieure_au_reste_422(client, headers_accueil, commande):  # RG7
    client.patch(f"{URL}/{commande['id']}", json={"remise": 15_000}, headers=headers_accueil)
    r = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][0]['id']}", headers=headers_accueil)
    assert r.status_code == 422  # il ne resterait que 10 000 de prestations pour 15 000 de remise


def test_tailleur_ne_peut_pas_retirer_de_ligne_403(client, headers_tailleur, commande):
    r = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][1]['id']}", headers=headers_tailleur)
    assert r.status_code == 403
