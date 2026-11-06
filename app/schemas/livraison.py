"""Schémas des livraisons (routes 35 à 38). RG18 à RG20 : voir livraisons_service."""
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.enums import ModeLivraison, StatutLivraison

Adresse = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Livreur = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class LivraisonPlanification(BaseModel):
    """Route 35 (PUT) : planifie ou replanifie. L'adresse est obligatoire à domicile (RG18, service)."""

    mode: ModeLivraison
    date_prevue: date
    adresse: Adresse | None = None
    livreur: Livreur | None = None
    notes: str | None = None


class LivraisonConfirmation(BaseModel):
    """Route 37 : corps facultatif. date_effective vaut aujourd'hui par défaut."""

    date_effective: date | None = None
    autoriser_solde_impaye: bool = False


class LivraisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    mode: ModeLivraison
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: StatutLivraison
    notes: str | None


class LivraisonTournee(LivraisonRead):
    """Élément de la route 38 (liste de tournée)."""

    numero_commande: str
    client_nom: str
    client_telephone: str
    solde_commande: int
