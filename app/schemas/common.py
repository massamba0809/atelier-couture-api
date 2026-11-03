"""Schémas communs : pagination des listes (section 8 de l'énoncé).

Réponse : {"items": [...], "total": n, "limit": n, "offset": n}.
Paramètres : limit = 20 par défaut (100 maximum), offset = 0.

Usage dans un router :

    @router.get("", response_model=Page[ClientRead])
    def lister(pagination: Pagination = Depends(), db: Session = Depends(get_db)):
        return clients_service.lister(db, pagination.limit, pagination.offset)
"""
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")

LIMIT_DEFAUT = 20
LIMIT_MAX = 100


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Pagination:
    """Dépendance FastAPI : lit et valide limit et offset (422 hors bornes)."""

    def __init__(
        self,
        limit: int = Query(
            LIMIT_DEFAUT, ge=1, le=LIMIT_MAX, description=f"Nombre d'éléments (1 à {LIMIT_MAX})."
        ),
        offset: int = Query(0, ge=0, description="Nombre d'éléments à sauter."),
    ) -> None:
        self.limit = limit
        self.offset = offset
