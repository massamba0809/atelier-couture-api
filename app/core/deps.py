"""Dépendances FastAPI partagées : utilisateur connecté et contrôle des rôles."""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import Interdit, NonAuthentifie
from app.core.security import decode_access_token
from app.models.enums import Role
from app.models.utilisateur import Utilisateur

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Utilisateur:
    """401 si pas de jeton, jeton invalide/expiré ou compte désactivé (RG22)."""
    if not token:
        raise NonAuthentifie("Authentification requise.")
    sujet = decode_access_token(token)
    if sujet is None or not sujet.isdigit():
        raise NonAuthentifie("Jeton invalide ou expiré.")
    user = db.get(Utilisateur, int(sujet))
    if user is None or not user.actif:
        raise NonAuthentifie("Compte inconnu ou désactivé.")
    return user


def require_roles(*roles: Role):
    """Autorise les rôles donnés (+ admin, qui peut tout faire). 403 sinon.

    Usage :  user = Depends(require_roles(Role.accueil))
    """
    autorises = set(roles) | {Role.admin}

    def verificateur(user: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if user.role not in autorises:
            raise Interdit("Droits insuffisants pour cette action.")
        return user

    return verificateur
