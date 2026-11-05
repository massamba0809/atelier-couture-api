"""Routes 18 à 23 : mesures. RG2, RG3, RG4."""
from datetime import date

import pytest

from app.models.client import Client
from app.models.enums import Role
from app.models.mesure import Mesure
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
