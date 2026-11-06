"""Schémas des statistiques (routes 39 à 43, administrateur uniquement)."""
from datetime import date
from enum import Enum

from pydantic import BaseModel

from app.models.enums import Statut


class Granularite(str, Enum):
    jour = "jour"
    mois = "mois"


class TableauDeBord(BaseModel):
    """Route 39."""

    chiffre_affaires_mois: int
    encaisse_mois: int
    nb_commandes_mois: int
    reste_a_encaisser: int
    commandes_par_statut: dict[Statut, int]
    nb_commandes_en_retard: int
    commandes_pretes_a_livrer: int
    livraisons_du_jour: int


class PeriodeChiffreAffaires(BaseModel):
    periode: str  # « 2026-11-05 » (jour) ou « 2026-11 » (mois)
    chiffre_affaires: int
    encaisse: int


class ChiffreAffaires(BaseModel):
    """Route 40."""

    granularite: Granularite
    date_debut: date
    date_fin: date
    periodes: list[PeriodeChiffreAffaires]


class VentesTypeVetement(BaseModel):
    """Élément de la route 41."""

    type_vetement_id: int
    nom: str
    quantite_vendue: int
    chiffre_affaires: int


class TopClient(BaseModel):
    """Élément de la route 42."""

    client_id: int
    nom: str
    prenom: str
    telephone: str
    nb_commandes: int
    chiffre_affaires: int
    solde_du: int


class Impaye(BaseModel):
    """Élément de la route 43."""

    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: Statut
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool
