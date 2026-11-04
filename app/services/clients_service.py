"""Règles de gestion des clients.

Responsable : Massamba (RG1). Le reste du service (création, doublons,
suppression RG4...) est à compléter.
"""
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import DonneesInvalides
from app.core.errors import Conflit, Introuvable
from app.models.client import Client
from app.models.commande import Commande
from app.models.enums import Genre, Statut
from app.models.mesure import Mesure
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.pagination import paginer

_SEPARATEURS = re.compile(r"[\s.\-()]")
_FORME_VALIDE = re.compile(r"^\+?\d{6,20}$")


def normaliser_telephone(brut: str) -> str:
    """RG1 : « 77 123 45 67 » et « 771234567 » désignent le même client.

    Supprime espaces, points, tirets et parenthèses ; valide 6 à 20 chiffres
    avec un « + » initial facultatif. Lève DonneesInvalides (422) sinon.
    """
    nettoye = _SEPARATEURS.sub("", brut or "")
    if not _FORME_VALIDE.match(nettoye):
        raise DonneesInvalides(
            "Numéro de téléphone invalide : 6 à 20 chiffres, « + » initial facultatif."
        )
    return nettoye


# --- Routes 7 à 13 -----------------------------------------------------------


def _verifier_telephone_libre(db: Session, telephone: str, sauf_id: int | None = None) -> None:
    """RG1 : 409 si un autre client a déjà ce numéro (déjà normalisé)."""
    requete = select(Client.id).where(Client.telephone == telephone)
    if sauf_id is not None:
        requete = requete.where(Client.id != sauf_id)  # garder son propre numéro n'est pas un doublon
    if db.scalar(requete) is not None:
        raise Conflit(f"Un client existe déjà avec le téléphone {telephone}.")


def creer_client(db: Session, donnees: ClientCreate) -> Client:
    champs = donnees.model_dump()
    champs["telephone"] = normaliser_telephone(champs["telephone"])  # RG1
    _verifier_telephone_libre(db, champs["telephone"])
    client = Client(**champs)
    db.add(client)
    db.flush()
    return client


def lister_clients(
    db: Session, q: str | None, genre: Genre | None, limit: int, offset: int
) -> dict[str, Any]:
    """Route 8 : triés par nom puis prénom ; q cherche dans nom, prénom et téléphone."""
    requete = select(Client)
    if q:
        motif = f"%{q.lower()}%"
        conditions = [func.lower(Client.nom).like(motif), func.lower(Client.prenom).like(motif)]
        # Le téléphone est stocké normalisé : « 77 12 » doit trouver « 771234567 ».
        tel = _SEPARATEURS.sub("", q)
        if tel:
            conditions.append(Client.telephone.like(f"%{tel}%"))
        requete = requete.where(or_(*conditions))
    if genre is not None:
        requete = requete.where(Client.genre == genre)
    requete = requete.order_by(Client.nom, Client.prenom, Client.id)
    return paginer(db, requete, limit, offset)


def obtenir_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise Introuvable(f"Client {client_id} introuvable.")
    return client


def modifier_client(db: Session, client_id: int, donnees: ClientUpdate) -> Client:
    client = obtenir_client(db, client_id)
    champs = donnees.model_dump(exclude_unset=True)
    if "telephone" in champs:
        champs["telephone"] = normaliser_telephone(champs["telephone"])  # RG1
        _verifier_telephone_libre(db, champs["telephone"], sauf_id=client.id)
    for champ, valeur in champs.items():
        setattr(client, champ, valeur)
    db.flush()
    return client


def supprimer_client(db: Session, client_id: int) -> None:
    """Route 11 : RG4, 409 si le client a des commandes. Ses mesures sont supprimées avec lui."""
    client = obtenir_client(db, client_id)
    nb = db.scalar(select(func.count(Commande.id)).where(Commande.client_id == client.id))
    if nb:
        raise Conflit(
            f"Impossible de supprimer le client {client.id} : il a {nb} commande(s)."
        )
    db.delete(client)  # cascade ORM : supprime aussi ses mesures
    db.flush()


def lister_commandes_du_client(db: Session, client_id: int, limit: int, offset: int) -> dict[str, Any]:
    """Route 12 : la plus récente d'abord."""
    client = obtenir_client(db, client_id)
    requete = (
        select(Commande)
        .where(Commande.client_id == client.id)
        .order_by(Commande.date_commande.desc(), Commande.id.desc())
    )
    return paginer(db, requete, limit, offset)


def resumer_client(db: Session, client_id: int) -> dict[str, Any]:
    """Route 13 : chiffres du client, commandes annulées exclues."""
    client = obtenir_client(db, client_id)
    nb, ca, paye, derniere = db.execute(
        select(
            func.count(Commande.id),
            func.coalesce(func.sum(Commande.montant_total), 0),
            func.coalesce(func.sum(Commande.montant_paye), 0),
            func.max(Commande.date_commande),
        ).where(Commande.client_id == client.id, Commande.statut != Statut.annulee)
    ).one()
    a_des_mesures = db.scalar(select(Mesure.id).where(Mesure.client_id == client.id).limit(1))
    return {
        "nb_commandes": nb,
        "chiffre_affaires": ca,
        "total_paye": paye,
        "solde_du": ca - paye,
        "derniere_commande": derniere,
        "a_des_mesures": a_des_mesures is not None,
    }
