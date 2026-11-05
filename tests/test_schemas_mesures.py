"""Schémas des mesures : RG2 (au moins une mesure, chacune 0 < x <= 300)."""
import pytest
from pydantic import ValidationError

from app.models.mesure import CHAMPS_MESURES
from app.schemas.mesure import MesureCreate, MesureRead, MesureUpdate


def test_les_schemas_couvrent_les_18_mesures():
    assert set(CHAMPS_MESURES) <= MesureCreate.model_fields.keys()
    assert set(CHAMPS_MESURES) <= MesureUpdate.model_fields.keys()
    assert set(CHAMPS_MESURES) <= MesureRead.model_fields.keys()


def test_creation_avec_une_seule_mesure_acceptee():
    mesure = MesureCreate(tour_cou=38)
    assert mesure.tour_cou == 38
    assert mesure.date_prise is None  # le service mettra la date du jour


def test_creation_sans_aucune_mesure_refusee():  # RG2
    with pytest.raises(ValidationError, match="au moins une mesure"):
        MesureCreate(notes="client pressé")


@pytest.mark.parametrize("valeur", [0, -5, 300.5])
def test_mesure_hors_bornes_refusee(valeur):  # RG2
    with pytest.raises(ValidationError):
        MesureCreate(tour_cou=valeur)


def test_300_cm_exactement_accepte():  # RG2 : « ne dépasse pas 300 »
    assert MesureCreate(taille_cm=300).taille_cm == 300


def test_modification_ne_garde_que_les_champs_envoyes():
    correction = MesureUpdate(tour_cou=39, tour_taille=None)
    assert correction.model_dump(exclude_unset=True) == {"tour_cou": 39, "tour_taille": None}


def test_modification_date_prise_nulle_refusee():
    with pytest.raises(ValidationError):
        MesureUpdate(date_prise=None)
