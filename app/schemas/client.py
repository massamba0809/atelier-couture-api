"""Schémas des clients (routes 7 à 13). RG1 : le téléphone est normalisé par le service."""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator

from app.models.enums import Genre, Statut

Nom = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# Forme brute (« 77 123 45 67 ») : la validation fine (RG1) est faite par normaliser_telephone.
Telephone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Adresse = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class ClientCreate(BaseModel):
    nom: Nom
    prenom: Nom
    telephone: Telephone
    email: EmailStr | None = None
    adresse: Adresse | None = None
    genre: Genre | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    """PATCH : seuls les champs envoyés changent. nom, prenom et telephone ne peuvent pas être vidés."""

    nom: Nom | None = None
    prenom: Nom | None = None
    telephone: Telephone | None = None
    email: EmailStr | None = None
    adresse: Adresse | None = None
    genre: Genre | None = None
    notes: str | None = None

    @field_validator("nom", "prenom", "telephone")
    @classmethod
    def non_nul(cls, valeur):
        # Appelé seulement pour les champs envoyés : un null explicite est refusé (422).
        if valeur is None:
            raise ValueError("ne peut pas être vide")
        return valeur


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    adresse: str | None
    genre: Genre | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CommandeDuClient(BaseModel):
    """Élément de la route 12 : vue résumée d'une commande du client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    statut: Statut
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int


class ClientResume(BaseModel):
    """Route 13. Les commandes annulées sont exclues de tous les chiffres."""

    nb_commandes: int
    chiffre_affaires: int
    total_paye: int
    solde_du: int
    derniere_commande: date | None
    a_des_mesures: bool
