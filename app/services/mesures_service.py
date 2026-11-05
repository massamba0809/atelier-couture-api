"""Règles de gestion des mesures (routes 18 à 23).

Responsable : Sine. RG2, RG3, RG4.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mesure import Mesure


def dernieres_mesures(db: Session, client_id: int) -> Mesure | None:
    """RG3 : la prise de mesures la plus récente du client, ou None s'il n'en a aucune.

    Contrat avec les commandes (RG9). En cas d'égalité de date, la dernière saisie
    (id le plus grand) l'emporte.
    """
    requete = (
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
        .limit(1)
    )
    return db.scalars(requete).first()
