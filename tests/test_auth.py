from tests.conftest import MOT_DE_PASSE, creer_utilisateur
from app.models.enums import Role


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_ok_et_me(client, headers_admin):
    r = client.get("/api/v1/auth/me", headers=headers_admin)
    assert r.status_code == 200
    corps = r.json()
    assert corps["role"] == "admin"
    assert "mot_de_passe_hash" not in corps  # RG21


def test_login_mauvais_mot_de_passe(client, db):
    u = creer_utilisateur(db, Role.accueil)
    r = client.post("/api/v1/auth/login", data={"username": u.email, "password": "faux"})
    assert r.status_code == 401


def test_login_message_identique_email_inconnu_ou_mdp_faux(client, db):  # RG23
    u = creer_utilisateur(db, Role.accueil)
    r1 = client.post("/api/v1/auth/login", data={"username": u.email, "password": "faux"})
    r2 = client.post("/api/v1/auth/login", data={"username": "inconnu@x.sn", "password": "faux"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


def test_compte_desactive_refuse_meme_avec_jeton_valide(client, db):  # RG22
    u = creer_utilisateur(db, Role.accueil)
    from tests.conftest import se_connecter

    headers = se_connecter(client, u.email)
    u.actif = False
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_sans_jeton_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401
