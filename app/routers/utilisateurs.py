"""Routes 3 à 6 : comptes utilisateurs (admin). Responsable : Massamba. RG21, RG24.

Schémas : app/schemas/utilisateur.py. Logique : app/services/utilisateurs_service.py.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurRead, UtilisateurUpdate
from app.services import utilisateurs_service

# require_roles() sans argument : admin uniquement.
router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])


@router.post("", response_model=UtilisateurRead, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: UtilisateurCreate,
    _: Utilisateur = Depends(require_roles()),
    db: Session = Depends(get_db),
):
    utilisateur = utilisateurs_service.creer_utilisateur(db, donnees)
    db.commit()
    return utilisateur


@router.get("", response_model=list[UtilisateurRead])
def lister(_: Utilisateur = Depends(require_roles()), db: Session = Depends(get_db)):
    return utilisateurs_service.lister_utilisateurs(db)


@router.get("/{utilisateur_id}", response_model=UtilisateurRead)
def obtenir(
    utilisateur_id: int,
    _: Utilisateur = Depends(require_roles()),
    db: Session = Depends(get_db),
):
    return utilisateurs_service.obtenir_utilisateur(db, utilisateur_id)


@router.patch("/{utilisateur_id}", response_model=UtilisateurRead)
def modifier(
    utilisateur_id: int,
    donnees: UtilisateurUpdate,
    admin: Utilisateur = Depends(require_roles()),
    db: Session = Depends(get_db),
):
    utilisateur = utilisateurs_service.modifier_utilisateur(db, utilisateur_id, donnees, admin)
    db.commit()
    return utilisateur
