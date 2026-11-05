"""Routes 32 à 34 : paiements. Responsable : Sine. RG16, RG17.

Schémas : app/schemas/paiement.py. Logique : app/services/paiements_service.py.
Chemins mixtes (/commandes/{id}/paiements et /paiements/{id}) : pas de prefix.
Encaisser : accueil (et admin). Consulter : tous. Annuler : admin uniquement.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.enums import Role
from app.models.utilisateur import Utilisateur
from app.schemas.paiement import PaiementCreate, PaiementRead
from app.services import paiements_service

router = APIRouter(tags=["Paiements"])


@router.post(
    "/commandes/{commande_id}/paiements",
    response_model=PaiementRead,
    status_code=status.HTTP_201_CREATED,
)
def encaisser(
    commande_id: int,
    donnees: PaiementCreate,
    user: Utilisateur = Depends(require_roles(Role.accueil)),
    db: Session = Depends(get_db),
):
    paiement = paiements_service.enregistrer_paiement(db, commande_id, donnees, user)
    db.commit()
    return paiement


@router.get("/commandes/{commande_id}/paiements", response_model=list[PaiementRead])
def lister(
    commande_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return paiements_service.lister_paiements(db, commande_id)


@router.delete("/paiements/{paiement_id}", status_code=status.HTTP_204_NO_CONTENT)
def annuler(
    paiement_id: int,
    _: Utilisateur = Depends(require_roles()),  # admin uniquement
    db: Session = Depends(get_db),
):
    paiements_service.annuler_paiement(db, paiement_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
