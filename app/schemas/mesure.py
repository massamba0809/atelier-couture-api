"""Schémas des mesures (routes 18 à 23). RG2 : au moins une mesure, chacune 0 < x <= 300 cm."""
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.mesure import CHAMPS_MESURES

# Une mesure en centimètres : strictement positive, au plus 300 (RG2).
Centimetres = Annotated[float, Field(gt=0, le=300)]


class MesuresValeurs(BaseModel):
    """Les 18 mesures facultatives, partagées par la création et la modification."""

    taille_cm: Centimetres | None = None
    tour_cou: Centimetres | None = None
    carrure_dos: Centimetres | None = None
    longueur_epaule: Centimetres | None = None
    tour_poitrine: Centimetres | None = None
    tour_taille: Centimetres | None = None
    tour_bassin: Centimetres | None = None
    longueur_manche: Centimetres | None = None
    tour_bras: Centimetres | None = None
    tour_poignet: Centimetres | None = None
    longueur_dos: Centimetres | None = None
    longueur_haut: Centimetres | None = None
    longueur_pantalon: Centimetres | None = None
    tour_cuisse: Centimetres | None = None
    tour_genou: Centimetres | None = None
    bas_pantalon: Centimetres | None = None
    entrejambe: Centimetres | None = None
    longueur_robe: Centimetres | None = None


class MesureCreate(MesuresValeurs):
    """Route 18. date_prise vaut aujourd'hui par défaut ; prise_par_id = utilisateur connecté."""

    date_prise: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def au_moins_une_mesure(self):
        # RG2 : une prise doit contenir au moins une mesure.
        if all(getattr(self, champ) is None for champ in CHAMPS_MESURES):
            raise ValueError("une prise doit contenir au moins une mesure")
        return self


class MesureUpdate(MesuresValeurs):
    """Route 22 (PATCH) : seuls les champs envoyés changent.

    Envoyer null efface une mesure. « Au moins une mesure après correction »
    se vérifie dans le service, car il faut connaître les valeurs déjà en base.
    """

    date_prise: date | None = None
    notes: str | None = None

    @field_validator("date_prise")
    @classmethod
    def date_non_nulle(cls, valeur):
        # Appelé seulement si date_prise est envoyée : un null explicite est refusé (422).
        if valeur is None:
            raise ValueError("ne peut pas être vide")
        return valeur


class MesureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    date_prise: date
    prise_par_id: int
    notes: str | None

    taille_cm: float | None
    tour_cou: float | None
    carrure_dos: float | None
    longueur_epaule: float | None
    tour_poitrine: float | None
    tour_taille: float | None
    tour_bassin: float | None
    longueur_manche: float | None
    tour_bras: float | None
    tour_poignet: float | None
    longueur_dos: float | None
    longueur_haut: float | None
    longueur_pantalon: float | None
    tour_cuisse: float | None
    tour_genou: float | None
    bas_pantalon: float | None
    entrejambe: float | None
    longueur_robe: float | None
