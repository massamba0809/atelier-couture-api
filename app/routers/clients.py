"""Routes 7 à 13 : clients. Responsable : Massamba. RG1, RG4.

Schémas : app/schemas/client.py. Logique : app/services/clients_service.py.
Lecture, création et modification : tout utilisateur connecté (tableau des routes).
Suppression : admin uniquement.
"""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.enums import Genre
from app.models.utilisateur import Utilisateur
from app.schemas.client import (
    ClientCreate,
    ClientRead,
    ClientResume,
    ClientUpdate,
    CommandeDuClient,
)
from app.schemas.common import Page, Pagination
from app.services import clients_service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: ClientCreate,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = clients_service.creer_client(db, donnees)
    db.commit()
    return client


@router.get("", response_model=Page[ClientRead])
def lister(
    q: str | None = Query(
        None, min_length=2, description="Recherche dans nom, prénom et téléphone (2 caractères minimum)."
    ),
    genre: Genre | None = None,
    pagination: Pagination = Depends(),
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return clients_service.lister_clients(db, q, genre, pagination.limit, pagination.offset)


@router.get("/{client_id}", response_model=ClientRead)
def obtenir(
    client_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return clients_service.obtenir_client(db, client_id)


@router.patch("/{client_id}", response_model=ClientRead)
def modifier(
    client_id: int,
    donnees: ClientUpdate,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = clients_service.modifier_client(db, client_id, donnees)
    db.commit()
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    client_id: int,
    _: Utilisateur = Depends(require_roles()),  # admin uniquement
    db: Session = Depends(get_db),
):
    clients_service.supprimer_client(db, client_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/commandes", response_model=Page[CommandeDuClient])
def commandes(
    client_id: int,
    pagination: Pagination = Depends(),
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return clients_service.lister_commandes_du_client(
        db, client_id, pagination.limit, pagination.offset
    )


@router.get("/{client_id}/resume", response_model=ClientResume)
def resume(
    client_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return clients_service.resumer_client(db, client_id)
