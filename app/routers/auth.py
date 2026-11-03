"""Routes 1 et 2 : /auth/login et /auth/me.

Modèle à suivre pour les autres routers : le router vérifie les droits, appelle
un service, puis valide la transaction. Aucune règle de gestion ici.
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.auth import Token, UtilisateurRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Formulaire OAuth2 : username = e-mail, password = mot de passe."""
    token, expires_in = auth_service.authentifier(db, form.username, form.password)
    return Token(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UtilisateurRead)
def me(user: Utilisateur = Depends(get_current_user)):
    return user
