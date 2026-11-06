"""Schémas des commandes (routes 24 à 31). Montants en FCFA, calculés par le serveur (RG7).

Les champs calculés (client_nom, solde, en_retard, sous_total...) sont préparés par
commandes_service (vue_resume, vue_detail) : ces schémas ne font que décrire la réponse.
"""
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models.enums import ModeLivraison, Statut, StatutLivraison
from app.schemas.paiement import PaiementRead

Montant = Annotated[int, Field(ge=0)]


class LigneCreate(BaseModel):
    """Une prestation commandée. prix_unitaire vaut le prix du catalogue s'il est omis (RG6)."""

    type_vetement_id: int
    quantite: int = Field(1, ge=1)
    prix_unitaire: Montant | None = None
    description: str | None = None


class CommandeCreate(BaseModel):
    """Route 24. Numéro, statut et montants sont fixés par le serveur."""

    client_id: int
    mesure_id: int | None = None
    lignes: list[LigneCreate] = Field(min_length=1)
    remise: Montant = 0
    date_livraison_prevue: date | None = None
    notes: str | None = None


class CommandeUpdate(BaseModel):
    """Route 27 (PATCH) : seuls les champs envoyés changent. mesure_id et notes peuvent être vidés."""

    mesure_id: int | None = None
    date_livraison_prevue: date | None = None
    remise: Montant | None = None
    notes: str | None = None

    @field_validator("date_livraison_prevue", "remise")
    @classmethod
    def non_nul(cls, valeur):
        # Appelé seulement pour les champs envoyés : un null explicite est refusé (422).
        if valeur is None:
            raise ValueError("ne peut pas être vide")
        return valeur


class ChangementStatut(BaseModel):
    """Route 28. Le commentaire est obligatoire pour annuler une commande qui a reçu un acompte (RG14)."""

    statut: Statut
    commentaire: Annotated[str, StringConstraints(strip_whitespace=True)] | None = None


class HistoriqueRead(BaseModel):
    """Route 29 : une ligne de l'historique des statuts (RG15)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ancien_statut: Statut | None
    nouveau_statut: Statut
    commentaire: str | None
    utilisateur_id: int
    date_changement: datetime


class LigneRead(BaseModel):
    id: int
    type_vetement_id: int
    type_vetement_nom: str
    description: str | None
    quantite: int
    prix_unitaire: int
    sous_total: int


class LivraisonDeCommande(BaseModel):
    """Livraison affichée dans le détail d'une commande (route 26)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: ModeLivraison
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: StatutLivraison
    notes: str | None


class CommandeResume(BaseModel):
    """Élément de la liste (route 25)."""

    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: Statut
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool


class CommandeRead(CommandeResume):
    """Détail complet (routes 24, 26 et suivantes)."""

    mesure_id: int | None
    date_livraison_reelle: date | None
    remise: int
    notes: str | None
    cree_par_id: int
    created_at: datetime
    updated_at: datetime
    lignes: list[LigneRead]
    paiements: list[PaiementRead]
    livraison: LivraisonDeCommande | None
