"""Schémas des paiements (routes 32 à 34). RG16 : montant strictement positif."""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import ModePaiement

Reference = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


class PaiementCreate(BaseModel):
    """Route 32. date_paiement vaut aujourd'hui par défaut ; enregistre_par_id = utilisateur connecté."""

    montant: int = Field(gt=0, description="Montant en FCFA, strictement positif.")
    mode: ModePaiement
    reference: Reference | None = None
    date_paiement: date | None = None


class PaiementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    montant: int
    mode: ModePaiement
    reference: str | None
    date_paiement: date
    enregistre_par_id: int
    created_at: datetime
