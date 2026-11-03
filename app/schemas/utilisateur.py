"""Schémas des comptes utilisateurs (routes 3 à 6). RG21 : le mot de passe n'est jamais renvoyé."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models.enums import Role

NomComplet = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
# RG21 : 8 caractères minimum. Pas de strip : les espaces font partie du mot de passe.
MotDePasse = Annotated[str, Field(min_length=8, max_length=128)]


class UtilisateurCreate(BaseModel):
    email: EmailStr
    nom_complet: NomComplet
    mot_de_passe: MotDePasse
    role: Role


class UtilisateurUpdate(BaseModel):
    """PATCH : seuls les champs envoyés changent. L'e-mail n'est pas modifiable."""

    nom_complet: NomComplet | None = None
    role: Role | None = None
    actif: bool | None = None
    mot_de_passe: MotDePasse | None = None

    @field_validator("nom_complet", "role", "actif", "mot_de_passe")
    @classmethod
    def non_nul(cls, valeur):
        # Appelé seulement pour les champs envoyés : un null explicite est refusé (422).
        if valeur is None:
            raise ValueError("ne peut pas être vide")
        return valeur


class UtilisateurRead(BaseModel):
    """Lecture d'un compte. Jamais de mot_de_passe_hash ici (RG21)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nom_complet: str
    role: Role
    actif: bool
    created_at: datetime
