"""Initialisation : `python -m app.seed`

Crée le premier administrateur (variables d'environnement ADMIN_*) et le
catalogue de départ (annexe B). Peut être relancé sans créer de doublons.
"""
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.catalogue import TypeVetement
from app.models.enums import Role
from app.models.utilisateur import Utilisateur

CATALOGUE_DEPART = [
    ("Boubou", "Boubou homme en bazin ou brodé", 35_000, 10),
    ("Costume 2 pièces", "Veste et pantalon", 85_000, 14),
    ("Robe", "Robe sur mesure", 30_000, 7),
    ("Ensemble wax", "Tenue deux pièces en wax", 25_000, 7),
    ("Chemise", "Chemise sur mesure", 15_000, 5),
    ("Pantalon", "Pantalon sur mesure", 12_000, 4),
    ("Retouche", "Ourlet, rétrécissement, remplacement de fermeture", 3_000, 2),
]


def run() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Utilisateur).where(Utilisateur.email == settings.admin_email)) is None:
            db.add(
                Utilisateur(
                    email=settings.admin_email,
                    nom_complet=settings.admin_nom_complet,
                    mot_de_passe_hash=hash_password(settings.admin_password),
                    role=Role.admin,
                    actif=True,
                )
            )
            print(f"Administrateur créé : {settings.admin_email}")

        for nom, description, prix_base, delai_jours in CATALOGUE_DEPART:
            if db.scalar(select(TypeVetement).where(TypeVetement.nom == nom)) is None:
                db.add(
                    TypeVetement(
                        nom=nom, description=description, prix_base=prix_base,
                        delai_jours=delai_jours, actif=True,
                    )
                )
                print(f"Prestation ajoutée : {nom}")
        db.commit()


if __name__ == "__main__":
    run()
