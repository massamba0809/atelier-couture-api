"""Routes 18 à 23 : mesures. RG2, RG3, RG4."""
from datetime import date

import pytest

from app.core.errors import Conflit, DonneesInvalides, Introuvable
from app.models.client import Client
from app.models.commande import Commande
from app.models.enums import Role
from app.models.mesure import Mesure
from app.schemas.mesure import MesureCreate, MesureUpdate
from app.services import mesures_service
from tests.conftest import creer_utilisateur


@pytest.fixture()
def tailleur(db):
    return creer_utilisateur(db, Role.tailleur, email="tailleur-mesures@atelier.sn")


@pytest.fixture()
def fatou(db):
    cliente = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    db.add(cliente)
    db.commit()
    return cliente


def inserer_mesure(db, client_id, auteur, jour, **mesures):
    mesure = Mesure(client_id=client_id, prise_par_id=auteur.id, date_prise=jour, **mesures)
    db.add(mesure)
    db.commit()
    return mesure


# --- dernieres_mesures (RG3, contrat avec les commandes) ----------------------


def test_dernieres_mesures_sans_mesure_renvoie_none(db, fatou):
    assert mesures_service.dernieres_mesures(db, fatou.id) is None


def test_dernieres_mesures_prend_la_date_la_plus_recente(db, fatou, tailleur):
    inserer_mesure(db, fatou.id, tailleur, date(2026, 3, 1), tour_cou=38)
    recente = inserer_mesure(db, fatou.id, tailleur, date(2026, 5, 1), tour_cou=39)
    inserer_mesure(db, fatou.id, tailleur, date(2026, 4, 1), tour_cou=40)  # saisie après, mais plus ancienne

    assert mesures_service.dernieres_mesures(db, fatou.id).id == recente.id


def test_dernieres_mesures_meme_date_la_derniere_saisie_gagne(db, fatou, tailleur):
    inserer_mesure(db, fatou.id, tailleur, date(2026, 5, 1), tour_cou=38)
    seconde = inserer_mesure(db, fatou.id, tailleur, date(2026, 5, 1), tour_cou=39)

    assert mesures_service.dernieres_mesures(db, fatou.id).id == seconde.id


def test_dernieres_mesures_ignore_les_autres_clients(db, fatou, tailleur):
    awa = Client(nom="Ndiaye", prenom="Awa", telephone="781112233")
    db.add(awa)
    db.commit()
    inserer_mesure(db, awa.id, tailleur, date(2026, 6, 1), tour_cou=36)

    assert mesures_service.dernieres_mesures(db, fatou.id) is None


# --- Service : création, lecture (routes 18 à 21) -----------------------------


def test_creer_mesure_date_du_jour_et_auteur(db, fatou, tailleur):  # route 18
    mesure = mesures_service.creer_mesure(db, fatou.id, MesureCreate(tour_cou=38), tailleur)
    assert mesure.id is not None
    assert mesure.date_prise == date.today()
    assert mesure.prise_par_id == tailleur.id
    assert mesure.tour_cou == 38


def test_creer_mesure_client_inconnu_404(db, tailleur):
    with pytest.raises(Introuvable):
        mesures_service.creer_mesure(db, 999, MesureCreate(tour_cou=38), tailleur)


def test_historique_le_plus_recent_d_abord(db, fatou, tailleur):  # route 19, RG3
    ancienne = inserer_mesure(db, fatou.id, tailleur, date(2026, 1, 1), tour_cou=37)
    recente = inserer_mesure(db, fatou.id, tailleur, date(2026, 2, 1), tour_cou=38)
    ids = [m.id for m in mesures_service.lister_mesures(db, fatou.id)]
    assert ids == [recente.id, ancienne.id]


def test_derniere_mesure_404_si_aucune(db, fatou):  # route 20
    with pytest.raises(Introuvable, match="aucune prise de mesures"):
        mesures_service.obtenir_dernieres_mesures(db, fatou.id)


def test_obtenir_mesure_inconnue_404(db):  # route 21
    with pytest.raises(Introuvable):
        mesures_service.obtenir_mesure(db, 999)


# --- Service : correction (route 22, RG2) -------------------------------------


def test_corriger_ne_change_que_les_champs_envoyes(db, fatou, tailleur):
    mesure = inserer_mesure(db, fatou.id, tailleur, date(2026, 1, 1), tour_cou=38, tour_taille=80)
    mesures_service.modifier_mesure(db, mesure.id, MesureUpdate(tour_cou=39))
    assert mesure.tour_cou == 39
    assert mesure.tour_taille == 80  # non envoyé : inchangé


def test_corriger_peut_effacer_une_mesure_s_il_en_reste(db, fatou, tailleur):
    mesure = inserer_mesure(db, fatou.id, tailleur, date(2026, 1, 1), tour_cou=38, tour_taille=80)
    mesures_service.modifier_mesure(db, mesure.id, MesureUpdate(tour_taille=None))
    assert mesure.tour_taille is None


def test_corriger_en_supprimant_toutes_les_mesures_422(db, fatou, tailleur):  # RG2
    mesure = inserer_mesure(db, fatou.id, tailleur, date(2026, 1, 1), tour_cou=38)
    with pytest.raises(DonneesInvalides):
        mesures_service.modifier_mesure(db, mesure.id, MesureUpdate(tour_cou=None))
    assert mesure.tour_cou == 38  # rien n'a été modifié


# --- Service : suppression (route 23, RG4) ------------------------------------


def test_supprimer_mesure_non_utilisee(db, fatou, tailleur):
    mesure = inserer_mesure(db, fatou.id, tailleur, date(2026, 1, 1), tour_cou=38)
    mesures_service.supprimer_mesure(db, mesure.id)
    assert db.get(Mesure, mesure.id) is None


def test_supprimer_mesure_utilisee_par_une_commande_409(db, fatou, tailleur):  # RG4
    mesure = inserer_mesure(db, fatou.id, tailleur, date(2026, 1, 1), tour_cou=38)
    db.add(Commande(
        numero="CMD-2026-00001", client_id=fatou.id, mesure_id=mesure.id,
        date_livraison_prevue=date(2026, 1, 15), cree_par_id=tailleur.id,
    ))
    db.commit()
    with pytest.raises(Conflit, match="utilisée par 1 commande"):
        mesures_service.supprimer_mesure(db, mesure.id)
