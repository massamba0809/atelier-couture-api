"""Erreurs de validation (422) : {"detail": "Données invalides : champ : explication ; ..."}.

Aucune route paginée ni route à corps JSON n'existe encore dans main : les cas
détaillés passent par une mini-application qui utilise le gestionnaire de app.main.
"""
import enum

import pytest
from fastapi import Depends, FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr, Field

from app.main import app, erreur_validation_handler


class Genre(str, enum.Enum):
    homme = "homme"
    femme = "femme"


class Corps(BaseModel):
    nom: str = Field(min_length=1, max_length=5)
    mot_de_passe: str = Field(min_length=8)
    email: EmailStr | None = None
    genre: Genre | None = None
    quantite: int = 1
    prix: float = 0
    actif: bool = True


def pagination(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict:
    return {"limit": limit, "offset": offset}


@pytest.fixture()
def mini_client():
    mini = FastAPI()
    mini.add_exception_handler(RequestValidationError, erreur_validation_handler)

    @mini.post("/objets")
    def creer(corps: Corps):
        return corps

    @mini.get("/objets")
    def lister(p: dict = Depends(pagination)):
        return p

    return TestClient(mini)


VALIDE = {"nom": "Diop", "mot_de_passe": "secret1234"}


def detail(r) -> str:
    assert r.status_code == 422
    corps = r.json()
    assert list(corps) == ["detail"]
    assert isinstance(corps["detail"], str)  # une seule chaîne, pas une liste
    return corps["detail"]


# Branchement sur l'application réelle
def test_gestionnaire_enregistre_sur_l_application():
    assert app.exception_handlers[RequestValidationError] is erreur_validation_handler


def test_route_reelle_champ_manquant(client):
    r = client.post("/api/v1/auth/login", data={"password": "x"})
    assert detail(r) == "Données invalides : username : champ obligatoire"


# Cas demandés
def test_champ_manquant(mini_client):
    r = mini_client.post("/objets", json={"nom": "Diop"})
    assert detail(r) == "Données invalides : mot_de_passe : champ obligatoire"


def test_valeur_trop_courte_avec_minimum(mini_client):
    r = mini_client.post("/objets", json={**VALIDE, "mot_de_passe": "court"})
    assert detail(r) == "Données invalides : mot_de_passe : trop court, minimum 8 caractère(s)"


def test_parametre_de_requete_invalide(mini_client):
    r = mini_client.get("/objets?limit=0")
    assert detail(r) == "Données invalides : limit : doit être supérieur ou égal à 1"


def test_plusieurs_erreurs_separees_par_point_virgule(mini_client):
    r = mini_client.post("/objets", json={})
    assert detail(r) == (
        "Données invalides : nom : champ obligatoire ; mot_de_passe : champ obligatoire"
    )


# Autres traductions
@pytest.mark.parametrize(
    "modif, attendu",
    [
        ({"nom": "Ndiayeee"}, "nom : trop long, maximum 5 caractère(s)"),
        ({"quantite": "deux"}, "quantite : nombre entier invalide"),
        ({"quantite": 1.5}, "quantite : nombre entier invalide"),
        ({"prix": "cher"}, "prix : nombre invalide"),
        ({"genre": "autre"}, "genre : valeur non autorisée, valeurs possibles : 'homme', 'femme'"),
        ({"email": "pas-un-mail"}, "email : adresse e-mail invalide"),
    ],
)
def test_traductions(mini_client, modif, attendu):
    r = mini_client.post("/objets", json={**VALIDE, **modif})
    assert detail(r) == f"Données invalides : {attendu}"


def test_parametre_au_dessus_du_maximum(mini_client):
    r = mini_client.get("/objets?limit=101")
    assert detail(r) == "Données invalides : limit : doit être inférieur ou égal à 100"


def test_repli_sur_le_message_d_origine(mini_client):
    r = mini_client.post("/objets", json={**VALIDE, "actif": "peut-etre"})
    assert detail(r).startswith("Données invalides : actif : ")
