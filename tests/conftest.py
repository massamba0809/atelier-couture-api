"""Fixtures communes. Les tests utilisent SQLite en mémoire (autorisé pour les tests).

Variables d'environnement factices posées AVANT l'import de l'application.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "cle-de-test")
os.environ.setdefault("ADMIN_PASSWORD", "motdepasse-test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.enums import Role
from app.models.utilisateur import Utilisateur

MOT_DE_PASSE = "secret1234"


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)  # uniquement pour les tests
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture()
def client(db: Session):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def creer_utilisateur(db: Session, role: Role, email: str | None = None, actif: bool = True):
    user = Utilisateur(
        email=email or f"{role.value}@atelier.sn",
        nom_complet=f"Test {role.value}",
        mot_de_passe_hash=hash_password(MOT_DE_PASSE),
        role=role,
        actif=actif,
    )
    db.add(user)
    db.commit()
    return user


def se_connecter(client: TestClient, email: str, mot_de_passe: str = MOT_DE_PASSE) -> dict:
    """Renvoie les en-têtes Authorization prêts à l'emploi."""
    r = client.post("/api/v1/auth/login", data={"username": email, "password": mot_de_passe})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def headers_admin(client, db):
    u = creer_utilisateur(db, Role.admin)
    return se_connecter(client, u.email)


@pytest.fixture()
def headers_accueil(client, db):
    u = creer_utilisateur(db, Role.accueil)
    return se_connecter(client, u.email)


@pytest.fixture()
def headers_tailleur(client, db):
    u = creer_utilisateur(db, Role.tailleur)
    return se_connecter(client, u.email)
