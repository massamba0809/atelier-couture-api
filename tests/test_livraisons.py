"""Routes 35 à 38 : livraisons. RG18, RG19, RG20, droits par rôle (annexe A, étapes 7 et 8)."""
from datetime import date, timedelta

import pytest

from app.models.catalogue import TypeVetement
from app.models.client import Client
from app.models.commande import Commande, HistoriqueStatut, LigneCommande
from app.models.enums import ModePaiement, Role, Statut
from app.models.paiement import Paiement
from app.services.commandes_service import recalculer_montants
from tests.conftest import creer_utilisateur

URL_COMMANDES = "/api/v1/commandes"
AUJOURD_HUI = date.today()


@pytest.fixture()
def auteur(db):
    return creer_utilisateur(db, Role.accueil, email="auteur-livraisons@atelier.sn")


@pytest.fixture()
def commande(db, auteur) -> Commande:
    """Commande « terminee » de 77 000 FCFA, rien de payé, sans livraison."""
    cliente = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    boubou = TypeVetement(nom="Boubou", prix_base=35_000, delai_jours=10)
    pantalon = TypeVetement(nom="Pantalon", prix_base=12_000, delai_jours=4)
    db.add_all([cliente, boubou, pantalon])
    db.flush()
    cmd = Commande(
        numero="CMD-2026-00001", client_id=cliente.id, statut=Statut.terminee,
        date_commande=AUJOURD_HUI - timedelta(days=10), date_livraison_prevue=AUJOURD_HUI,
        remise=5_000, cree_par_id=auteur.id,
    )
    cmd.lignes.append(LigneCommande(type_vetement_id=boubou.id, quantite=2, prix_unitaire=35_000))
    cmd.lignes.append(LigneCommande(type_vetement_id=pantalon.id, quantite=1, prix_unitaire=12_000))
    db.add(cmd)
    recalculer_montants(cmd)
    db.commit()
    return cmd


def solder(db, commande, auteur, montant=None):
    """Ajoute un paiement (par la liste, comme le veut le contrat) puis recalcule."""
    montant = commande.solde if montant is None else montant
    commande.paiements.append(Paiement(montant=montant, mode=ModePaiement.wave, enregistre_par_id=auteur.id))
    recalculer_montants(commande)
    db.commit()


def planifier(client, commande, headers, **corps):
    corps = {"mode": "retrait_atelier", "date_prevue": AUJOURD_HUI.isoformat(), **corps}
    return client.put(f"{URL_COMMANDES}/{commande.id}/livraison", json=corps, headers=headers)


def confirmer(client, commande, headers, corps=None):
    return client.post(f"{URL_COMMANDES}/{commande.id}/livraison/confirmer", json=corps, headers=headers)


# --- Route 35 : planifier / replanifier (RG18) --------------------------------


def test_planifier_a_domicile(client, db, headers_accueil, commande):
    demain = AUJOURD_HUI + timedelta(days=1)
    r = planifier(client, commande, headers_accueil, mode="domicile",
                  date_prevue=demain.isoformat(), adresse="HLM 4, Dakar", livreur="Moussa")
    assert r.status_code == 200
    corps = r.json()
    assert corps["statut"] == "planifiee" and corps["adresse"] == "HLM 4, Dakar"
    db.refresh(commande)
    assert commande.date_livraison_prevue == demain  # RG18 : met à jour la commande


def test_domicile_sans_adresse_422(client, headers_accueil, commande):  # RG18
    r = planifier(client, commande, headers_accueil, mode="domicile")
    assert r.status_code == 422
    assert "adresse" in r.json()["detail"]


def test_replanifier_ne_cree_pas_de_seconde_livraison(client, headers_accueil, commande):  # RG18
    premiere = planifier(client, commande, headers_accueil).json()
    seconde = planifier(client, commande, headers_accueil, mode="domicile", adresse="Rufisque").json()
    assert seconde["id"] == premiere["id"]
    assert seconde["mode"] == "domicile"


def test_date_prevue_avant_la_commande_422(client, headers_accueil, commande):
    r = planifier(client, commande, headers_accueil,
                  date_prevue=(commande.date_commande - timedelta(days=1)).isoformat())
    assert r.status_code == 422


@pytest.mark.parametrize("statut", [Statut.livree, Statut.annulee])
def test_planifier_commande_livree_ou_annulee_409(client, db, headers_accueil, commande, statut):
    commande.statut = statut
    db.commit()
    assert planifier(client, commande, headers_accueil).status_code == 409


def test_tailleur_ne_peut_pas_planifier_403(client, headers_tailleur, commande):
    assert planifier(client, commande, headers_tailleur).status_code == 403


# --- Route 36 : consulter -----------------------------------------------------


def test_consulter_la_livraison(client, headers_accueil, headers_tailleur, commande):
    planifier(client, commande, headers_accueil)
    r = client.get(f"{URL_COMMANDES}/{commande.id}/livraison", headers=headers_tailleur)
    assert r.status_code == 200
    assert r.json()["mode"] == "retrait_atelier"


def test_aucune_livraison_planifiee_404(client, headers_accueil, commande):
    r = client.get(f"{URL_COMMANDES}/{commande.id}/livraison", headers=headers_accueil)
    assert r.status_code == 404


# --- Route 37 : confirmer (RG19, RG20) ----------------------------------------


def test_confirmer_commande_non_soldee_409_avec_montant(client, headers_accueil, commande):  # ét. 7
    r = confirmer(client, commande, headers_accueil)
    assert r.status_code == 409
    assert "77000 FCFA" in r.json()["detail"]


def test_confirmer_commande_soldee(client, db, headers_accueil, commande, auteur):  # annexe A, ét. 8
    planifier(client, commande, headers_accueil)
    solder(db, commande, auteur)
    r = confirmer(client, commande, headers_accueil)
    assert r.status_code == 200
    assert r.json()["statut"] == "livree"
    assert r.json()["date_effective"] == AUJOURD_HUI.isoformat()
    db.refresh(commande)
    assert commande.statut == Statut.livree  # RG20
    assert commande.date_livraison_reelle == AUJOURD_HUI
    assert commande.solde == 0


def test_confirmer_ecrit_l_historique(client, db, headers_accueil, commande, auteur):  # RG15, RG20
    solder(db, commande, auteur)
    confirmer(client, commande, headers_accueil)
    derniere = db.query(HistoriqueStatut).filter_by(commande_id=commande.id).all()[-1]
    assert derniere.nouveau_statut == Statut.livree


def test_solde_impaye_autorise_mention_dans_l_historique(client, db, headers_accueil, commande, auteur):
    solder(db, commande, auteur, montant=50_000)  # reste 27 000
    r = confirmer(client, commande, headers_accueil, {"autoriser_solde_impaye": True})
    assert r.status_code == 200
    db.refresh(commande)
    assert commande.statut == Statut.livree
    assert commande.solde == 27_000  # RG19 : la dette reste visible
    derniere = db.query(HistoriqueStatut).filter_by(commande_id=commande.id).all()[-1]
    assert derniere.commentaire == "Livré avec solde impayé de 27000 FCFA"


def test_sans_planification_retrait_atelier_cree(client, db, headers_accueil, commande, auteur):  # RG20
    solder(db, commande, auteur)
    hier = (AUJOURD_HUI - timedelta(days=1)).isoformat()
    r = confirmer(client, commande, headers_accueil, {"date_effective": hier})
    assert r.status_code == 200
    assert r.json()["mode"] == "retrait_atelier"
    assert r.json()["date_effective"] == hier


@pytest.mark.parametrize("statut", [Statut.en_couture, Statut.livree, Statut.annulee])
def test_confirmer_commande_non_terminee_409(client, db, headers_accueil, commande, statut):  # RG19
    commande.statut = statut
    db.commit()
    r = confirmer(client, commande, headers_accueil)
    assert r.status_code == 409
    assert "terminee" in r.json()["detail"]


def test_tailleur_ne_peut_pas_confirmer_403(client, headers_tailleur, commande):
    assert confirmer(client, commande, headers_tailleur).status_code == 403


# --- Route 38 : liste de tournée ----------------------------------------------


def test_tournee_triee_par_date_avec_infos_client(client, db, headers_accueil, commande, auteur):
    planifier(client, commande, headers_accueil,
              date_prevue=(AUJOURD_HUI + timedelta(days=3)).isoformat())
    autre_cliente = Client(nom="Ndiaye", prenom="Awa", telephone="781112233")
    db.add(autre_cliente)
    db.flush()
    autre = Commande(
        numero="CMD-2026-00002", client_id=autre_cliente.id, statut=Statut.terminee,
        date_commande=AUJOURD_HUI, date_livraison_prevue=AUJOURD_HUI, cree_par_id=auteur.id,
    )
    db.add(autre)
    db.commit()
    planifier(client, autre, headers_accueil, date_prevue=(AUJOURD_HUI + timedelta(days=1)).isoformat())

    r = client.get("/api/v1/livraisons", headers=headers_accueil)
    assert r.status_code == 200
    corps = r.json()
    assert corps["total"] == 2 and corps["limit"] == 20 and corps["offset"] == 0
    assert [i["numero_commande"] for i in corps["items"]] == ["CMD-2026-00002", "CMD-2026-00001"]
    fatou = corps["items"][1]
    assert fatou["client_nom"] == "Fatou Diop"
    assert fatou["client_telephone"] == "771234567"
    assert fatou["solde_commande"] == 77_000


def test_tournee_filtres(client, db, headers_accueil, commande, auteur):
    planifier(client, commande, headers_accueil,
              date_prevue=(AUJOURD_HUI + timedelta(days=5)).isoformat())
    url = "/api/v1/livraisons"
    jour = (AUJOURD_HUI + timedelta(days=1)).isoformat()
    assert client.get(url, params={"date_max": jour}, headers=headers_accueil).json()["total"] == 0
    assert client.get(url, params={"statut": "planifiee"}, headers=headers_accueil).json()["total"] == 1
    assert client.get(url, params={"statut": "livree"}, headers=headers_accueil).json()["total"] == 0
