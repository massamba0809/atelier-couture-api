"""Routes 39 à 43 : statistiques (admin uniquement). Annexe A, étapes 9 et 10."""
from datetime import date, timedelta

import pytest

from app.models.catalogue import TypeVetement
from app.models.client import Client
from app.models.commande import Commande, LigneCommande
from app.models.enums import ModePaiement, Role, Statut
from app.models.livraison import Livraison
from app.models.paiement import Paiement
from app.services.commandes_service import recalculer_montants
from tests.conftest import creer_utilisateur

URL = "/api/v1/statistiques"
AUJOURD_HUI = date.today()
DEBUT_MOIS = AUJOURD_HUI.replace(day=1)


@pytest.fixture()
def donnees(db):
    """Jeu de données du mois courant :
    - Fatou : CMD-1 (2 boubous + 1 pantalon − 5 000 = 77 000), payée 20 000, en couture, en retard ;
    - Fatou : CMD-2 (1 robe = 30 000), terminée, soldée, livraison prévue aujourd'hui ;
    - Awa   : CMD-3 (1 boubou = 35 000), annulée, acompte 10 000 → exclue du CA, comptée dans l'encaissé.
    """
    auteur = creer_utilisateur(db, Role.accueil, email="auteur-stats@atelier.sn")
    fatou = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    awa = Client(nom="Ndiaye", prenom="Awa", telephone="781112233")
    boubou = TypeVetement(nom="Boubou", prix_base=35_000, delai_jours=10)
    pantalon = TypeVetement(nom="Pantalon", prix_base=12_000, delai_jours=4)
    robe = TypeVetement(nom="Robe", prix_base=30_000, delai_jours=7)
    db.add_all([fatou, awa, boubou, pantalon, robe])
    db.flush()

    def commande(numero, client, statut, lignes, remise=0, prevue=AUJOURD_HUI, paye=0):
        cmd = Commande(
            numero=numero, client_id=client.id, statut=statut, date_commande=DEBUT_MOIS,
            date_livraison_prevue=prevue, remise=remise, cree_par_id=auteur.id,
        )
        for type_, quantite in lignes:
            cmd.lignes.append(
                LigneCommande(type_vetement_id=type_.id, quantite=quantite, prix_unitaire=type_.prix_base)
            )
        if paye:
            cmd.paiements.append(
                Paiement(montant=paye, mode=ModePaiement.wave, date_paiement=DEBUT_MOIS,
                         enregistre_par_id=auteur.id)
            )
        db.add(cmd)
        recalculer_montants(cmd)
        return cmd

    commande("CMD-1", fatou, Statut.en_couture, [(boubou, 2), (pantalon, 1)], remise=5_000,
             prevue=AUJOURD_HUI - timedelta(days=1), paye=20_000)
    cmd2 = commande("CMD-2", fatou, Statut.terminee, [(robe, 1)], paye=30_000)
    commande("CMD-3", awa, Statut.annulee, [(boubou, 1)], paye=10_000)
    db.flush()
    db.add(Livraison(commande_id=cmd2.id, mode="retrait_atelier", date_prevue=AUJOURD_HUI))
    db.commit()


# --- Droits : tout le router est réservé à l'admin ----------------------------


@pytest.mark.parametrize("chemin", [
    "/tableau-de-bord", "/chiffre-affaires", "/types-vetement", "/top-clients", "/impayes",
])
def test_accueil_ne_voit_pas_les_statistiques_403(client, headers_accueil, chemin):  # annexe A, ét. 9
    assert client.get(URL + chemin, headers=headers_accueil).status_code == 403


def test_sans_jeton_401(client):
    assert client.get(f"{URL}/tableau-de-bord").status_code == 401


# --- Route 39 : tableau de bord -----------------------------------------------


def test_tableau_de_bord(client, headers_admin, donnees):
    r = client.get(f"{URL}/tableau-de-bord", headers=headers_admin)
    assert r.status_code == 200
    t = r.json()
    assert t["chiffre_affaires_mois"] == 107_000  # 77 000 + 30 000, l'annulée est exclue
    assert t["encaisse_mois"] == 60_000  # 20 000 + 30 000 + 10 000 (acompte de l'annulée compris)
    assert t["nb_commandes_mois"] == 2
    assert t["reste_a_encaisser"] == 57_000  # 57 000 + 0
    assert len(t["commandes_par_statut"]) == 8  # tous les statuts, même à 0
    assert t["commandes_par_statut"]["en_couture"] == 1
    assert t["commandes_par_statut"]["essayage"] == 0
    assert t["nb_commandes_en_retard"] == 1
    assert t["commandes_pretes_a_livrer"] == 1
    assert t["livraisons_du_jour"] == 1


def test_tableau_de_bord_base_vide(client, headers_admin):
    t = client.get(f"{URL}/tableau-de-bord", headers=headers_admin).json()
    assert t["chiffre_affaires_mois"] == 0 and t["reste_a_encaisser"] == 0
    assert set(t["commandes_par_statut"].values()) == {0}


# --- Route 40 : chiffre d'affaires par période --------------------------------


def test_chiffre_affaires_par_jour(client, headers_admin, donnees):
    r = client.get(f"{URL}/chiffre-affaires", headers=headers_admin)
    assert r.status_code == 200
    corps = r.json()
    assert corps["date_debut"] == DEBUT_MOIS.isoformat()
    assert corps["date_fin"] == AUJOURD_HUI.isoformat()
    assert corps["periodes"] == [
        {"periode": DEBUT_MOIS.isoformat(), "chiffre_affaires": 107_000, "encaisse": 60_000}
    ]  # seules les périodes avec activité


def test_chiffre_affaires_par_mois(client, headers_admin, donnees):
    r = client.get(f"{URL}/chiffre-affaires", params={"granularite": "mois"}, headers=headers_admin)
    assert r.json()["periodes"][0]["periode"] == DEBUT_MOIS.strftime("%Y-%m")


def test_chiffre_affaires_dates_inversees_422(client, headers_admin):
    r = client.get(
        f"{URL}/chiffre-affaires",
        params={"date_debut": "2026-11-10", "date_fin": "2026-11-01"},
        headers=headers_admin,
    )
    assert r.status_code == 422


def test_granularite_inconnue_422(client, headers_admin):
    r = client.get(f"{URL}/chiffre-affaires", params={"granularite": "semaine"}, headers=headers_admin)
    assert r.status_code == 422


# --- Route 41 : par type de vêtement ------------------------------------------


def test_ventes_par_type(client, headers_admin, donnees):
    r = client.get(f"{URL}/types-vetement", headers=headers_admin)
    assert r.status_code == 200
    assert [(v["nom"], v["quantite_vendue"], v["chiffre_affaires"]) for v in r.json()] == [
        ("Boubou", 2, 70_000),  # avant remise ; le boubou de la commande annulée est exclu
        ("Robe", 1, 30_000),
        ("Pantalon", 1, 12_000),
    ]


# --- Route 42 : meilleurs clients ---------------------------------------------


def test_top_clients(client, headers_admin, donnees):
    r = client.get(f"{URL}/top-clients", headers=headers_admin)
    assert r.status_code == 200
    top = r.json()
    assert len(top) == 1  # Awa n'a qu'une commande annulée
    assert (top[0]["prenom"], top[0]["nb_commandes"], top[0]["chiffre_affaires"], top[0]["solde_du"]) == (
        "Fatou", 2, 107_000, 57_000
    )


def test_top_clients_limite_invalide_422(client, headers_admin):
    assert client.get(f"{URL}/top-clients", params={"limite": 0}, headers=headers_admin).status_code == 422


# --- Route 43 : impayés -------------------------------------------------------


def test_impayes(client, headers_admin, donnees):  # annexe A, étape 10
    r = client.get(f"{URL}/impayes", headers=headers_admin)
    assert r.status_code == 200
    corps = r.json()
    assert corps["total"] == 1  # CMD-2 est soldée, CMD-3 est annulée
    impaye = corps["items"][0]
    assert impaye["numero"] == "CMD-1"
    assert impaye["solde"] == 57_000
    assert impaye["client_nom"] == "Fatou Diop"
    assert impaye["en_retard"] is True
