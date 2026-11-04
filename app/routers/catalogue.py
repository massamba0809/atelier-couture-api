"""Routes 14 à 17 : catalogue des prestations. Responsable : Massamba.

Schémas : app/schemas/catalogue.py. Logique : app/services/catalogue_service.py.
Lecture : tout utilisateur connecté. Création et modification : admin uniquement.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.utilisateur import Utilisateur
from app.schemas.catalogue import TypeVetementCreate, TypeVetementRead, TypeVetementUpdate
from app.services import catalogue_service

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


@router.post("", response_model=TypeVetementRead, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: TypeVetementCreate,
    _: Utilisateur = Depends(require_roles()),  # admin uniquement
    db: Session = Depends(get_db),
):
    prestation = catalogue_service.creer_prestation(db, donnees)
    db.commit()
    return prestation


@router.get("", response_model=list[TypeVetementRead])
def lister(
    actifs_seulement: bool = Query(True, description="false pour inclure les prestations retirées."),
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return catalogue_service.lister_prestations(db, actifs_seulement)


@router.get("/{prestation_id}", response_model=TypeVetementRead)
def obtenir(
    prestation_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return catalogue_service.obtenir_prestation(db, prestation_id)


@router.patch("/{prestation_id}", response_model=TypeVetementRead)
def modifier(
    prestation_id: int,
    donnees: TypeVetementUpdate,
    _: Utilisateur = Depends(require_roles()),  # admin uniquement
    db: Session = Depends(get_db),
):
    prestation = catalogue_service.modifier_prestation(db, prestation_id, donnees)
    db.commit()
    return prestation
