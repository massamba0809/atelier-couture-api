from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UtilisateurRead(BaseModel):
    """Lecture d'un compte. Jamais de mot_de_passe_hash ici (RG21)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nom_complet: str
    role: Role
    actif: bool
