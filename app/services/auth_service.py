"""Authentification (RG22, RG23)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NonAuthentifie
from app.core.security import create_access_token, verify_password
from app.models.utilisateur import Utilisateur


def authentifier(db: Session, email: str, mot_de_passe: str) -> tuple[str, int]:
    """Renvoie (jeton, expires_in).

    RG23 : même message que l'e-mail soit inconnu ou le mot de passe faux.
    """
    user = db.scalar(select(Utilisateur).where(Utilisateur.email == email))
    if user is None or not user.actif or not verify_password(mot_de_passe, user.mot_de_passe_hash):
        raise NonAuthentifie("Identifiants incorrects.")
    return create_access_token(str(user.id))
