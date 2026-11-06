"""Routes 35 à 38 : livraisons. Responsable : Sine. RG18, RG19, RG20.

Schémas : app/schemas/livraison.py. Logique : app/services/livraisons_service.py.
Chemins mixtes (/commandes/{id}/livraison et /livraisons) : pas de prefix.
Planifier et confirmer : accueil (et admin). Consulter : tous.
La confirmation passe la commande à « livree » via enregistrer_changement_statut
(historique RG15, avec la mention du solde impayé si autoriser_solde_impaye, RG19).
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.enums import Role, StatutLivraison
from app.models.utilisateur import Utilisateur
from app.schemas.common import Page, Pagination
from app.schemas.livraison import (
    LivraisonConfirmation,
    LivraisonPlanification,
    LivraisonRead,
    LivraisonTournee,
)
from app.services import livraisons_service

router = APIRouter(tags=["Livraisons"])


@router.put("/commandes/{commande_id}/livraison", response_model=LivraisonRead)
def planifier(
    commande_id: int,
    donnees: LivraisonPlanification,
    _: Utilisateur = Depends(require_roles(Role.accueil)),
    db: Session = Depends(get_db),
):
    livraison = livraisons_service.planifier_livraison(db, commande_id, donnees)
    db.commit()
    return livraison


@router.get("/commandes/{commande_id}/livraison", response_model=LivraisonRead)
def obtenir(
    commande_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return livraisons_service.obtenir_livraison(db, commande_id)


@router.post("/commandes/{commande_id}/livraison/confirmer", response_model=LivraisonRead)
def confirmer(
    commande_id: int,
    donnees: LivraisonConfirmation | None = None,  # corps facultatif
    user: Utilisateur = Depends(require_roles(Role.accueil)),
    db: Session = Depends(get_db),
):
    livraison = livraisons_service.confirmer_livraison(
        db, commande_id, donnees or LivraisonConfirmation(), user
    )
    db.commit()
    return livraison


@router.get("/livraisons", response_model=Page[LivraisonTournee])
def tournee(
    statut: StatutLivraison | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    pagination: Pagination = Depends(),
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return livraisons_service.lister_livraisons(
        db, statut, date_min, date_max, pagination.limit, pagination.offset
    )
