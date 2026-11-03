"""Hachage des mots de passe (Argon2) et jetons JWT.

NB : adaptez les imports si le requirements.txt du prof impose une autre
bibliothèque (python-jose, pwdlib, passlib...).
"""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


def hash_password(mot_de_passe: str) -> str:
    return _hasher.hash(mot_de_passe)


def verify_password(mot_de_passe: str, hash_enregistre: str) -> bool:
    try:
        return _hasher.verify(hash_enregistre, mot_de_passe)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(sujet: str) -> tuple[str, int]:
    """Renvoie (jeton, durée de validité en secondes)."""
    expires_in = settings.access_token_expire_minutes * 60
    expiration = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    token = jwt.encode(
        {"sub": sujet, "exp": expiration}, settings.secret_key, algorithm=settings.algorithm
    )
    return token, expires_in


def decode_access_token(token: str) -> str | None:
    """Renvoie le sujet du jeton, ou None s'il est invalide ou expiré."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
