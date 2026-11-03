"""Pagination d'une requête select : compte total + limit/offset.

Ne connaît pas HTTP : reçoit limit et offset déjà validés (schemas.common.Pagination).
"""
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginer(db: Session, requete: Select, limit: int, offset: int) -> dict[str, Any]:
    """Renvoie {"items", "total", "limit", "offset"}, prêt pour un response_model Page[XxxRead].

    `requete` sélectionne une entité (ex. select(Client).where(...).order_by(...)) :
    le tri doit y être fixé pour que les pages soient stables.
    """
    total = db.scalar(select(func.count()).select_from(requete.order_by(None).subquery()))
    items = db.scalars(requete.limit(limit).offset(offset)).all()
    return {"items": list(items), "total": total or 0, "limit": limit, "offset": offset}
