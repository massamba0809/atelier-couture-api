"""Routes 18 à 23 : mesures. Responsable : Sine. RG2, RG3, RG4.

Schémas : app/schemas/mesure.py. Logique : app/services/mesures_service.py.
Chemins mixtes (/clients/{id}/mesures et /mesures/{id}) : ce router n'a pas de prefix.
Lecture : tout utilisateur connecté. Prise, correction, suppression : tailleur (et admin).
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.enums import Role
from app.models.utilisateur import Utilisateur
from app.schemas.mesure import MesureCreate, MesureRead, MesureUpdate
from app.services import mesures_service

router = APIRouter(tags=["Mesures"])


@router.post(
    "/clients/{client_id}/mesures", response_model=MesureRead, status_code=status.HTTP_201_CREATED
)
def creer(
    client_id: int,
    donnees: MesureCreate,
    user: Utilisateur = Depends(require_roles(Role.tailleur)),
    db: Session = Depends(get_db),
):
    mesure = mesures_service.creer_mesure(db, client_id, donnees, user)
    db.commit()
    return mesure


@router.get("/clients/{client_id}/mesures", response_model=list[MesureRead])
def historique(
    client_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mesures_service.lister_mesures(db, client_id)


@router.get("/clients/{client_id}/mesures/derniere", response_model=MesureRead)
def derniere(
    client_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mesures_service.obtenir_dernieres_mesures(db, client_id)


@router.get("/mesures/{mesure_id}", response_model=MesureRead)
def obtenir(
    mesure_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mesures_service.obtenir_mesure(db, mesure_id)


@router.patch("/mesures/{mesure_id}", response_model=MesureRead)
def corriger(
    mesure_id: int,
    donnees: MesureUpdate,
    _: Utilisateur = Depends(require_roles(Role.tailleur)),
    db: Session = Depends(get_db),
):
    mesure = mesures_service.modifier_mesure(db, mesure_id, donnees)
    db.commit()
    return mesure


@router.delete("/mesures/{mesure_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    mesure_id: int,
    _: Utilisateur = Depends(require_roles(Role.tailleur)),
    db: Session = Depends(get_db),
):
    mesures_service.supprimer_mesure(db, mesure_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
