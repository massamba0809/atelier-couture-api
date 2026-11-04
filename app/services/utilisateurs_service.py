"""Comptes utilisateurs (routes 3 à 6) : RG21 (mot de passe haché), RG24 (pas d'auto-rétrogradation)."""
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflit, Introuvable
from app.core.security import hash_password
from app.models.enums import Role
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurUpdate


def _verifier_email_libre(db: Session, email: str) -> None:
    """409 si l'e-mail est déjà pris (sans tenir compte des majuscules)."""
    existe = db.scalar(select(Utilisateur.id).where(func.lower(Utilisateur.email) == email.lower()))
    if existe is not None:
        raise Conflit(f"Un compte existe déjà avec l'e-mail {email}.")


def creer_utilisateur(db: Session, donnees: UtilisateurCreate) -> Utilisateur:
    _verifier_email_libre(db, donnees.email)
    utilisateur = Utilisateur(
        email=donnees.email,
        nom_complet=donnees.nom_complet,
        mot_de_passe_hash=hash_password(donnees.mot_de_passe),  # RG21
        role=donnees.role,
        actif=True,
    )
    db.add(utilisateur)
    db.flush()
    return utilisateur


def lister_utilisateurs(db: Session) -> Sequence[Utilisateur]:
    """Tous les comptes, triés par nom."""
    return db.scalars(select(Utilisateur).order_by(Utilisateur.nom_complet, Utilisateur.id)).all()


def obtenir_utilisateur(db: Session, utilisateur_id: int) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise Introuvable(f"Utilisateur {utilisateur_id} introuvable.")
    return utilisateur


def modifier_utilisateur(
    db: Session, utilisateur_id: int, donnees: UtilisateurUpdate, auteur: Utilisateur
) -> Utilisateur:
    """Modifie seulement les champs envoyés. `auteur` est l'administrateur connecté."""
    utilisateur = obtenir_utilisateur(db, utilisateur_id)
    champs = donnees.model_dump(exclude_unset=True)

    # RG24 : un administrateur ne peut ni se désactiver ni retirer son propre rôle admin.
    if utilisateur.id == auteur.id:
        if champs.get("actif") is False:
            raise Conflit("Vous ne pouvez pas désactiver votre propre compte.")
        if "role" in champs and champs["role"] != Role.admin:
            raise Conflit("Vous ne pouvez pas retirer votre propre rôle d'administrateur.")

    if "mot_de_passe" in champs:
        utilisateur.mot_de_passe_hash = hash_password(champs.pop("mot_de_passe"))  # RG21
    for champ, valeur in champs.items():
        setattr(utilisateur, champ, valeur)
    db.flush()
    return utilisateur
