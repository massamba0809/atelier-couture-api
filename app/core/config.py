"""Configuration lue depuis les variables d'environnement (fichier .env).

Aucun secret ne doit être écrit dans le code ni dans Git.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Premier administrateur créé par `python -m app.seed`
    admin_email: str = "admin@atelier.sn"
    admin_password: str
    admin_nom_complet: str = "Administrateur"


settings = Settings()
