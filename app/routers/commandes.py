"""Routes 24 à 31 : commandes. Responsable : Massamba. RG5 à RG15.

Schémas : app/schemas/commande.py. Logique : app/services/commandes_service.py.
Accueil (et admin) : créer, modifier, gérer les lignes. Tous : consulter et changer
le statut (le service applique RG13 et RG14 : le tailleur ne peut pas annuler).
"""
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.enums import Role, Statut
from app.models.utilisateur import Utilisateur
from app.schemas.commande import (
    ChangementStatut,
    CommandeCreate,
    CommandeRead,
    CommandeResume,
    CommandeUpdate,
    HistoriqueRead,
    LigneCreate,
)
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


@router.patch("/{commande_id}", response_model=CommandeRead)
def modifier(
    commande_id: int,
    donnees: CommandeUpdate,
    _: Utilisateur = Depends(require_roles(Role.accueil)),
    db: Session = Depends(get_db),
):
    commande = commandes_service.modifier_commande(db, commande_id, donnees)
    db.commit()
    return commandes_service.vue_detail(commande)


@router.post("/{commande_id}/statut", response_model=CommandeRead)
def changer_statut(
    commande_id: int,
    donnees: ChangementStatut,
    user: Utilisateur = Depends(get_current_user),  # tous ; RG14 vérifiée dans le service
    db: Session = Depends(get_db),
):
    commande = commandes_service.changer_statut(db, commande_id, donnees, user)
    db.commit()
    return commandes_service.vue_detail(commande)


@router.get("/{commande_id}/historique", response_model=list[HistoriqueRead])
def historique(
    commande_id: int,
    _: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return commandes_service.lister_historique(db, commande_id)


@router.post("/{commande_id}/lignes", response_model=CommandeRead, status_code=status.HTTP_201_CREATED)
def ajouter_ligne(
    commande_id: int,
    donnees: LigneCreate,
    _: Utilisateur = Depends(require_roles(Role.accueil)),
    db: Session = Depends(get_db),
):
    commande = commandes_service.ajouter_ligne(db, commande_id, donnees)
    db.commit()
    return commandes_service.vue_detail(commande)


@router.delete("/{commande_id}/lignes/{ligne_id}", response_model=CommandeRead)
def retirer_ligne(
    commande_id: int,
    ligne_id: int,
    _: Utilisateur = Depends(require_roles(Role.accueil)),
    db: Session = Depends(get_db),
):
    commande = commandes_service.retirer_ligne(db, commande_id, ligne_id)
    db.commit()
    return commandes_service.vue_detail(commande)
