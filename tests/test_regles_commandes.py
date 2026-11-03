"""Tests des règles pures (sans base de données) : RG1, RG5, RG7, RG8, RG11, RG13."""
from datetime import date

import pytest

from app.core.errors import Conflit, DonneesInvalides
from app.models.enums import Statut
from app.services import commandes_service as svc
from app.services.clients_service import normaliser_telephone


# RG1
@pytest.mark.parametrize("brut", ["77 123 45 67", "771234567", "77.123.45.67", "(77)-123-45-67"])
def test_telephone_normalise(brut):
    assert normaliser_telephone(brut) == "771234567"


def test_telephone_plus_initial_conserve():
    assert normaliser_telephone("+221 77 123 45 67") == "+221771234567"


@pytest.mark.parametrize("brut", ["", "abc", "12345", "77 12 ab 34 56"])
def test_telephone_invalide(brut):
    with pytest.raises(DonneesInvalides):
        normaliser_telephone(brut)


# RG5
def test_numero_commande():
    assert svc.formater_numero(2026, 17) == "CMD-2026-00017"


# RG7
def test_total_et_solde():
    total = svc.calculer_total([(2, 35_000), (1, 10_000)], remise=5_000)
    assert total == 75_000
    assert svc.calculer_solde(total, 20_000) == 55_000


# RG8
def test_date_livraison_par_defaut_plus_long_delai():
    assert svc.date_livraison_par_defaut(date(2026, 11, 2), [10, 4]) == date(2026, 11, 12)


# RG11
def test_en_retard():
    hier, auj = date(2026, 11, 1), date(2026, 11, 2)
    assert svc.est_en_retard(Statut.en_couture, hier, auj) is True
    assert svc.est_en_retard(Statut.livree, hier, auj) is False
    assert svc.est_en_retard(Statut.annulee, hier, auj) is False
    assert svc.est_en_retard(Statut.en_coupe, auj, auj) is False


# Workflow + RG13
@pytest.mark.parametrize(
    "actuel,nouveau",
    [
        (Statut.en_attente, Statut.en_coupe),
        (Statut.en_coupe, Statut.en_couture),
        (Statut.en_couture, Statut.essayage),
        (Statut.essayage, Statut.retouches),
        (Statut.retouches, Statut.essayage),
        (Statut.retouches, Statut.terminee),
        (Statut.en_attente, Statut.annulee),
    ],
)
def test_transitions_autorisees(actuel, nouveau):
    svc.verifier_transition(actuel, nouveau)  # ne lève pas


def test_transition_interdite_message_actionnable():
    with pytest.raises(Conflit) as e:
        svc.verifier_transition(Statut.en_attente, Statut.terminee)
    assert e.value.detail == (
        "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe"
    )


def test_meme_statut_refuse():
    with pytest.raises(Conflit):
        svc.verifier_transition(Statut.en_coupe, Statut.en_coupe)


def test_livree_impossible_par_la_route_statut():
    with pytest.raises(Conflit):
        svc.verifier_transition(Statut.terminee, Statut.livree)


@pytest.mark.parametrize("final", [Statut.livree, Statut.annulee])
def test_statuts_finaux(final):
    with pytest.raises(Conflit):
        svc.verifier_transition(final, Statut.en_coupe)
