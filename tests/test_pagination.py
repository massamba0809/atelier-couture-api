"""Pagination commune : Page[T], dépendance Pagination et services.pagination.paginer.

Aucune route paginée n'existe encore : la dépendance est testée sur une mini-application.
"""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.models.catalogue import TypeVetement
from app.schemas.common import Page, Pagination
from app.services.pagination import paginer


class PrestationTest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nom: str


def ajouter_prestations(db, n: int) -> None:
    for i in range(n):
        db.add(TypeVetement(nom=f"P{i:02d}", prix_base=1000, delai_jours=1))
    db.commit()


@pytest.fixture()
def mini_client(db):
    mini = FastAPI()

    @mini.get("/pagination")
    def lire_pagination(pagination: Pagination = Depends()):
        return {"limit": pagination.limit, "offset": pagination.offset}

    @mini.get("/prestations", response_model=Page[PrestationTest])
    def lister(pagination: Pagination = Depends()):
        requete = select(TypeVetement).order_by(TypeVetement.nom)
        return paginer(db, requete, pagination.limit, pagination.offset)

    return TestClient(mini)


# Dépendance Pagination
def test_valeurs_par_defaut(mini_client):
    assert mini_client.get("/pagination").json() == {"limit": 20, "offset": 0}


def test_limit_maximum_accepte(mini_client):
    assert mini_client.get("/pagination?limit=100&offset=5").json() == {"limit": 100, "offset": 5}


@pytest.mark.parametrize("params", ["limit=101", "limit=0", "offset=-1", "limit=abc"])
def test_parametres_hors_bornes_422(mini_client, params):
    assert mini_client.get(f"/pagination?{params}").status_code == 422


# paginer
def test_paginer_total_et_tranche(db):
    ajouter_prestations(db, 5)
    requete = select(TypeVetement).order_by(TypeVetement.nom)
    page = paginer(db, requete, limit=2, offset=1)
    assert page["total"] == 5
    assert [p.nom for p in page["items"]] == ["P01", "P02"]
    assert (page["limit"], page["offset"]) == (2, 1)


def test_paginer_total_respecte_le_filtre(db):
    ajouter_prestations(db, 5)
    requete = select(TypeVetement).where(TypeVetement.nom >= "P03").order_by(TypeVetement.nom)
    page = paginer(db, requete, limit=20, offset=0)
    assert page["total"] == 2
    assert [p.nom for p in page["items"]] == ["P03", "P04"]


def test_paginer_au_dela_de_la_fin(db):
    ajouter_prestations(db, 3)
    page = paginer(db, select(TypeVetement).order_by(TypeVetement.nom), limit=20, offset=10)
    assert page["items"] == []
    assert page["total"] == 3


def test_paginer_liste_vide(db):
    page = paginer(db, select(TypeVetement), limit=20, offset=0)
    assert page == {"items": [], "total": 0, "limit": 20, "offset": 0}


# Page[T] : du modèle SQLAlchemy au JSON
def test_reponse_page_au_format_de_l_enonce(db, mini_client):
    ajouter_prestations(db, 3)
    r = mini_client.get("/prestations?limit=2")
    assert r.status_code == 200
    assert r.json() == {"items": [{"nom": "P00"}, {"nom": "P01"}], "total": 3, "limit": 2, "offset": 0}
