"""Règles de gestion des mesures (routes 18 à 23).

Responsable : Sine. RG2, RG3, RG4.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflit, DonneesInvalides, Introuvable
from app.models.commande import Commande
from app.models.mesure import CHAMPS_MESURES, Mesure
from app.models.utilisateur import Utilisateur
from app.schemas.mesure import MesureCreate, MesureUpdate
from app.services.clients_service import obtenir_client


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


# --- Routes 18 à 23 -----------------------------------------------------------


def creer_mesure(db: Session, client_id: int, donnees: MesureCreate, auteur: Utilisateur) -> Mesure:
    """Route 18 : date du jour par défaut ; prise_par_id = utilisateur connecté. RG2 : voir le schéma."""
    obtenir_client(db, client_id)  # 404 si le client n'existe pas
    champs = donnees.model_dump()
    if champs["date_prise"] is None:
        champs["date_prise"] = date.today()
    mesure = Mesure(client_id=client_id, prise_par_id=auteur.id, **champs)
    db.add(mesure)
    db.flush()
    return mesure


def lister_mesures(db: Session, client_id: int) -> list[Mesure]:
    """Route 19 : historique complet (RG3), la plus récente d'abord."""
    obtenir_client(db, client_id)
    requete = (
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
    )
    return list(db.scalars(requete).all())


def obtenir_dernieres_mesures(db: Session, client_id: int) -> Mesure:
    """Route 20 : 404 si le client n'a aucune mesure."""
    obtenir_client(db, client_id)
    mesure = dernieres_mesures(db, client_id)
    if mesure is None:
        raise Introuvable(f"Le client {client_id} n'a aucune prise de mesures.")
    return mesure


def obtenir_mesure(db: Session, mesure_id: int) -> Mesure:
    """Route 21."""
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise Introuvable(f"Prise de mesures {mesure_id} introuvable.")
    return mesure


def modifier_mesure(db: Session, mesure_id: int, donnees: MesureUpdate) -> Mesure:
    """Route 22 : corrige les champs envoyés. 422 si la correction supprimait toutes les mesures (RG2)."""
    mesure = obtenir_mesure(db, mesure_id)
    champs = donnees.model_dump(exclude_unset=True)
    # Valeurs APRÈS correction : celles envoyées, sinon celles déjà en base.
    apres = {champ: champs.get(champ, getattr(mesure, champ)) for champ in CHAMPS_MESURES}
    if all(valeur is None for valeur in apres.values()):
        raise DonneesInvalides(
            "Correction refusée : une prise de mesures doit garder au moins une mesure."
        )
    for champ, valeur in champs.items():
        setattr(mesure, champ, valeur)
    db.flush()
    return mesure


def supprimer_mesure(db: Session, mesure_id: int) -> None:
    """Route 23 : RG4, 409 si une commande utilise ces mesures."""
    mesure = obtenir_mesure(db, mesure_id)
    nb = db.scalar(select(func.count(Commande.id)).where(Commande.mesure_id == mesure.id))
    if nb:
        raise Conflit(
            f"Impossible de supprimer la prise de mesures {mesure.id} : "
            f"elle est utilisée par {nb} commande(s)."
        )
    db.delete(mesure)
    db.flush()
