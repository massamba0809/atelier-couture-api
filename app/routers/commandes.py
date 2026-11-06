"""Routes 24 à 31 : commandes. Responsable : Massamba. RG5 à RG15.

Schémas : app/schemas/commande.py. Logique : app/services/commandes_service.py.
Fait : 24 (création, accueil), 25 (liste), 26 (détail).
TODO : PATCH /commandes/{id}, POST /commandes/{id}/statut, GET /commandes/{id}/historique,
POST /commandes/{id}/lignes, DELETE /commandes/{id}/lignes/{ligne_id}.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.enums import Role, Statut
from app.models.utilisateur import Utilisateur
from app.schemas.commande import CommandeCreate, CommandeRead, CommandeResume
from app.schemas.common import Page, Pagination
from app.services import commandes_service

router = APIRouter(prefix="/commandes", tags=["Commandes"])


@router.post("", response_model=CommandeRead, status_code=status.HTTP_201_CREATED)
def creer(
    donnees: CommandeCreate,
    user: Utilisateur = Depends(require_roles(Role.accueil)),
    db: Session = Depends(get_db),
):
    commande = commandes_service.creer_commande(db, donnees, user)
    db.commit()
    return commandes_service.vue_detail(commande)


@router.get("", response_model=Page[CommandeResume])
def lister(
    statut: Statut | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = Query(None, description="Date de commande minimale (incluse)."),
    date_max: date | None = Query(None, description="Date de commande maximale (incluse)."),
    numero: str | None = Query(None, description="Tout ou partie du numéro, ex. 2026-00017."),
    pagination: Pagination = Depends(),
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return commandes_service.lister_commandes(
        db, statut=statut, client_id=client_id, en_retard=en_retard, date_min=date_min,
        date_max=date_max, numero=numero, limit=pagination.limit, offset=pagination.offset,
    )


@router.get("/{commande_id}", response_model=CommandeRead)
def obtenir(
    commande_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return commandes_service.vue_detail(commandes_service.obtenir_commande(db, commande_id))
