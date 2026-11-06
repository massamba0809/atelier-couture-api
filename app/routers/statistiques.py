"""Routes 39 à 43 : statistiques. Responsable : Sine. Administrateur uniquement.

Logique : app/services/statistiques_service.py (définitions de la section 6).
Période par défaut (routes 40 à 42) : du 1er du mois à aujourd'hui ; 422 si date_debut > date_fin.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.schemas.common import Page, Pagination
from app.schemas.statistique import (
    ChiffreAffaires,
    Granularite,
    Impaye,
    TableauDeBord,
    TopClient,
    VentesTypeVetement,
)
from app.services import statistiques_service

# require_roles() sans argument : admin uniquement, pour TOUTES les routes du router.
router = APIRouter(
    prefix="/statistiques", tags=["Statistiques"], dependencies=[Depends(require_roles())]
)


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def tableau_de_bord(db: Session = Depends(get_db)):
    return statistiques_service.tableau_de_bord(db)


@router.get("/chiffre-affaires", response_model=ChiffreAffaires)
def chiffre_affaires(
    granularite: Granularite = Granularite.jour,
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    return statistiques_service.chiffre_affaires(db, granularite, date_debut, date_fin)


@router.get("/types-vetement", response_model=list[VentesTypeVetement])
def types_vetement(
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    return statistiques_service.ventes_par_type(db, date_debut, date_fin)


@router.get("/top-clients", response_model=list[TopClient])
def top_clients(
    date_debut: date | None = None,
    date_fin: date | None = None,
    limite: int = Query(10, ge=1, le=100, description="Nombre de clients (10 par défaut)."),
    db: Session = Depends(get_db),
):
    return statistiques_service.top_clients(db, date_debut, date_fin, limite)


@router.get("/impayes", response_model=Page[Impaye])
def impayes(pagination: Pagination = Depends(), db: Session = Depends(get_db)):
    return statistiques_service.impayes(db, pagination.limit, pagination.offset)
