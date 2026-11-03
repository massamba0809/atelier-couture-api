"""Routes 3 à 6 : comptes utilisateurs (admin). RG21, RG24, droits par rôle."""
import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.enums import Role
from app.models.utilisateur import Utilisateur
from tests.conftest import creer_utilisateur, se_connecter

URL = "/api/v1/utilisateurs"
NOUVEAU = {
    "email": "fatou@atelier.sn",
    "nom_complet": "Fatou Ndiaye",
    "mot_de_passe": "motdepasse8",
    "role": "accueil",
}


@pytest.fixture()
def id_admin(client, headers_admin) -> int:
    return client.get("/api/v1/auth/me", headers=headers_admin).json()["id"]


@pytest.fixture()
def tailleur(db) -> Utilisateur:
    return creer_utilisateur(db, Role.tailleur, email="moussa@atelier.sn")


# Route 3 : POST /utilisateurs
def test_creer_utilisateur_201(client, headers_admin):
    r = client.post(URL, json=NOUVEAU, headers=headers_admin)
    assert r.status_code == 201
    corps = r.json()
    assert corps["email"] == "fatou@atelier.sn"
    assert corps["nom_complet"] == "Fatou Ndiaye"
    assert corps["role"] == "accueil"
    assert corps["actif"] is True
    assert {"id", "created_at"} <= corps.keys()


def test_creer_utilisateur_peut_se_connecter(client, headers_admin):
    client.post(URL, json=NOUVEAU, headers=headers_admin)
    se_connecter(client, NOUVEAU["email"], NOUVEAU["mot_de_passe"])


def test_email_existant_409(client, headers_admin):
    assert client.post(URL, json=NOUVEAU, headers=headers_admin).status_code == 201
    r = client.post(URL, json=NOUVEAU, headers=headers_admin)
    assert r.status_code == 409
    assert r.json() == {"detail": "Un compte existe déjà avec l'e-mail fatou@atelier.sn."}


def test_email_existant_409_meme_avec_majuscules(client, headers_admin):
    client.post(URL, json=NOUVEAU, headers=headers_admin)
    r = client.post(URL, json={**NOUVEAU, "email": "Fatou@atelier.sn"}, headers=headers_admin)
    assert r.status_code == 409


def test_mot_de_passe_trop_court_422(client, headers_admin):  # RG21
    r = client.post(URL, json={**NOUVEAU, "mot_de_passe": "court12"}, headers=headers_admin)
    assert r.status_code == 422
    assert r.json() == {
        "detail": "Données invalides : mot_de_passe : trop court, minimum 8 caractère(s)"
    }


@pytest.mark.parametrize(
    "modif, champ",
    [
        ({"role": "patron"}, "role"),
        ({"email": "pas-un-mail"}, "email"),
        ({"nom_complet": "   "}, "nom_complet"),
    ],
)
def test_creation_donnees_invalides_422(client, headers_admin, modif, champ):
    r = client.post(URL, json={**NOUVEAU, **modif}, headers=headers_admin)
    assert r.status_code == 422
    assert r.json()["detail"].startswith(f"Données invalides : {champ} : ")


def test_creation_champ_manquant_422(client, headers_admin):
    sans_role = {k: v for k, v in NOUVEAU.items() if k != "role"}
    r = client.post(URL, json=sans_role, headers=headers_admin)
    assert r.json() == {"detail": "Données invalides : role : champ obligatoire"}


# RG21 : mot de passe haché, jamais renvoyé
def test_mot_de_passe_hache_argon2(client, db, headers_admin):
    client.post(URL, json=NOUVEAU, headers=headers_admin)
    u = db.scalar(select(Utilisateur).where(Utilisateur.email == NOUVEAU["email"]))
    assert u.mot_de_passe_hash != NOUVEAU["mot_de_passe"]
    assert u.mot_de_passe_hash.startswith("$argon2")
    assert verify_password(NOUVEAU["mot_de_passe"], u.mot_de_passe_hash)


def test_hash_jamais_expose(client, headers_admin, tailleur):
    reponses = [
        client.post(URL, json=NOUVEAU, headers=headers_admin),
        client.get(URL, headers=headers_admin),
        client.get(f"{URL}/{tailleur.id}", headers=headers_admin),
        client.patch(f"{URL}/{tailleur.id}", json={"mot_de_passe": "nouveau-mdp"}, headers=headers_admin),
    ]
    for r in reponses:
        assert r.status_code in (200, 201)
        assert "mot_de_passe" not in r.text  # ni mot_de_passe ni mot_de_passe_hash
        assert "argon2" not in r.text


# Route 4 : GET /utilisateurs
def test_lister_tries_par_nom(client, db, headers_admin):
    for email, nom in [("z@a.sn", "Zeynab Ba"), ("a@a.sn", "Awa Diallo"), ("m@a.sn", "Moussa Sow")]:
        client.post(URL, json={**NOUVEAU, "email": email, "nom_complet": nom}, headers=headers_admin)
    r = client.get(URL, headers=headers_admin)
    assert r.status_code == 200
    noms = [u["nom_complet"] for u in r.json()]
    assert noms == sorted(noms)
    assert {"Awa Diallo", "Moussa Sow", "Zeynab Ba", "Test admin"} == set(noms)


# Route 5 : GET /utilisateurs/{id}
def test_obtenir_utilisateur(client, headers_admin, tailleur):
    r = client.get(f"{URL}/{tailleur.id}", headers=headers_admin)
    assert r.status_code == 200
    assert r.json()["email"] == "moussa@atelier.sn"


def test_obtenir_utilisateur_inconnu_404(client, headers_admin):
    r = client.get(f"{URL}/9999", headers=headers_admin)
    assert r.status_code == 404
    assert r.json() == {"detail": "Utilisateur 9999 introuvable."}


# Route 6 : PATCH /utilisateurs/{id}
def test_patch_ne_change_que_les_champs_envoyes(client, headers_admin, tailleur):
    r = client.patch(f"{URL}/{tailleur.id}", json={"nom_complet": "Moussa Faye"}, headers=headers_admin)
    assert r.status_code == 200
    corps = r.json()
    assert corps["nom_complet"] == "Moussa Faye"
    assert (corps["email"], corps["role"], corps["actif"]) == ("moussa@atelier.sn", "tailleur", True)


def test_patch_role(client, headers_admin, tailleur):
    r = client.patch(f"{URL}/{tailleur.id}", json={"role": "accueil"}, headers=headers_admin)
    assert r.json()["role"] == "accueil"


def test_patch_desactiver_un_autre_compte(client, headers_admin, tailleur):
    headers_tailleur = se_connecter(client, tailleur.email)
    r = client.patch(f"{URL}/{tailleur.id}", json={"actif": False}, headers=headers_admin)
    assert r.status_code == 200
    assert r.json()["actif"] is False
    assert client.get("/api/v1/auth/me", headers=headers_tailleur).status_code == 401  # RG22


def test_patch_mot_de_passe(client, headers_admin, tailleur):
    r = client.patch(f"{URL}/{tailleur.id}", json={"mot_de_passe": "nouveau-mdp"}, headers=headers_admin)
    assert r.status_code == 200
    se_connecter(client, tailleur.email, "nouveau-mdp")
    ancien = client.post("/api/v1/auth/login", data={"username": tailleur.email, "password": "secret1234"})
    assert ancien.status_code == 401


def test_patch_mot_de_passe_trop_court_422(client, headers_admin, tailleur):  # RG21
    r = client.patch(f"{URL}/{tailleur.id}", json={"mot_de_passe": "court"}, headers=headers_admin)
    assert r.status_code == 422
    assert r.json() == {
        "detail": "Données invalides : mot_de_passe : trop court, minimum 8 caractère(s)"
    }


@pytest.mark.parametrize("champ", ["nom_complet", "role", "actif", "mot_de_passe"])
def test_patch_null_refuse_422(client, headers_admin, tailleur, champ):
    r = client.patch(f"{URL}/{tailleur.id}", json={champ: None}, headers=headers_admin)
    assert r.status_code == 422
    assert r.json() == {"detail": f"Données invalides : {champ} : ne peut pas être vide"}


def test_patch_inconnu_404(client, headers_admin):
    assert client.patch(f"{URL}/9999", json={"actif": True}, headers=headers_admin).status_code == 404


# RG24 : un admin ne peut ni se désactiver ni retirer son propre rôle admin
def test_admin_ne_peut_pas_se_desactiver_409(client, db, headers_admin, id_admin):
    r = client.patch(f"{URL}/{id_admin}", json={"actif": False}, headers=headers_admin)
    assert r.status_code == 409
    assert r.json() == {"detail": "Vous ne pouvez pas désactiver votre propre compte."}
    assert db.get(Utilisateur, id_admin).actif is True


@pytest.mark.parametrize("role", ["accueil", "tailleur"])
def test_admin_ne_peut_pas_retirer_son_role_409(client, db, headers_admin, id_admin, role):
    r = client.patch(f"{URL}/{id_admin}", json={"role": role}, headers=headers_admin)
    assert r.status_code == 409
    assert r.json() == {"detail": "Vous ne pouvez pas retirer votre propre rôle d'administrateur."}
    assert db.get(Utilisateur, id_admin).role == Role.admin


def test_admin_peut_modifier_son_nom_et_mot_de_passe(client, headers_admin, id_admin):
    r = client.patch(
        f"{URL}/{id_admin}",
        json={"nom_complet": "Mamadou", "mot_de_passe": "nouveau-mdp", "role": "admin", "actif": True},
        headers=headers_admin,
    )
    assert r.status_code == 200
    assert r.json()["nom_complet"] == "Mamadou"


def test_admin_peut_desactiver_un_autre_admin(client, db, headers_admin):
    autre = creer_utilisateur(db, Role.admin, email="patron2@atelier.sn")
    r = client.patch(f"{URL}/{autre.id}", json={"actif": False, "role": "accueil"}, headers=headers_admin)
    assert r.status_code == 200


# Droits : admin uniquement
ROUTES = [
    ("post", URL, NOUVEAU),
    ("get", URL, None),
    ("get", f"{URL}/1", None),
    ("patch", f"{URL}/1", {"nom_complet": "X"}),
]


@pytest.mark.parametrize("methode, url, corps", ROUTES)
@pytest.mark.parametrize("role", ["accueil", "tailleur"])
def test_accueil_et_tailleur_403(client, request, methode, url, corps, role):
    headers = request.getfixturevalue(f"headers_{role}")
    r = client.request(methode, url, json=corps, headers=headers)
    assert r.status_code == 403
    assert r.json() == {"detail": "Droits insuffisants pour cette action."}


@pytest.mark.parametrize("methode, url, corps", ROUTES)
def test_sans_jeton_401(client, methode, url, corps):
    assert client.request(methode, url, json=corps).status_code == 401
