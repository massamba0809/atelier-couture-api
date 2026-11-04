"""Catalogue des prestations (routes 14 à 17). Responsable : Massamba.

Désactiver une prestation (actif=false) ne touche pas aux commandes existantes :
leurs lignes gardent leur propre prix_unitaire.
"""
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflit, Introuvable
from app.models.catalogue import TypeVetement
from app.schemas.catalogue import TypeVetementCreate, TypeVetementUpdate


def _verifier_nom_libre(db: Session, nom: str, sauf_id: int | None = None) -> None:
    """409 si une autre prestation porte déjà ce nom (sans tenir compte des majuscules)."""
    requete = select(TypeVetement.id).where(func.lower(TypeVetement.nom) == nom.lower())
    if sauf_id is not None:
        requete = requete.where(TypeVetement.id != sauf_id)
    if db.scalar(requete) is not None:
        raise Conflit(f"Une prestation existe déjà avec le nom « {nom} ».")


def creer_prestation(db: Session, donnees: TypeVetementCreate) -> TypeVetement:
    _verifier_nom_libre(db, donnees.nom)
    prestation = TypeVetement(**donnees.model_dump(), actif=True)
    db.add(prestation)
    db.flush()
    return prestation


def lister_prestations(db: Session, actifs_seulement: bool = True) -> Sequence[TypeVetement]:
    """Route 15 : triées par nom ; seulement les actives, sauf actifs_seulement=False."""
    requete = select(TypeVetement)
    if actifs_seulement:
        requete = requete.where(TypeVetement.actif.is_(True))
    return db.scalars(requete.order_by(TypeVetement.nom, TypeVetement.id)).all()


def obtenir_prestation(db: Session, prestation_id: int) -> TypeVetement:
    """Route 16 : une prestation inactive reste consultable ; 404 seulement si elle n'existe pas."""
    prestation = db.get(TypeVetement, prestation_id)
    if prestation is None:
        raise Introuvable(f"Prestation {prestation_id} introuvable.")
    return prestation


def modifier_prestation(db: Session, prestation_id: int, donnees: TypeVetementUpdate) -> TypeVetement:
    prestation = obtenir_prestation(db, prestation_id)
    champs = donnees.model_dump(exclude_unset=True)
    if "nom" in champs:
        _verifier_nom_libre(db, champs["nom"], sauf_id=prestation.id)
    for champ, valeur in champs.items():
        setattr(prestation, champ, valeur)
    db.flush()
    return prestation
