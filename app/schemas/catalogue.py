"""Schémas du catalogue des prestations (routes 14 à 17). Montants en FCFA, délais en jours."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

NomPrestation = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Prix = Annotated[int, Field(ge=0)]
Delai = Annotated[int, Field(ge=0)]


class TypeVetementCreate(BaseModel):
    nom: NomPrestation
    description: str | None = None
    prix_base: Prix
    delai_jours: Delai


class TypeVetementUpdate(BaseModel):
    """PATCH : seuls les champs envoyés changent. actif=false retire la prestation du catalogue."""

    nom: NomPrestation | None = None
    description: str | None = None
    prix_base: Prix | None = None
    delai_jours: Delai | None = None
    actif: bool | None = None

    @field_validator("nom", "prix_base", "delai_jours", "actif")
    @classmethod
    def non_nul(cls, valeur):
        # Appelé seulement pour les champs envoyés : un null explicite est refusé (422).
        if valeur is None:
            raise ValueError("ne peut pas être vide")
        return valeur


class TypeVetementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    description: str | None
    prix_base: int
    delai_jours: int
    actif: bool
