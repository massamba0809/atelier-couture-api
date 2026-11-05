"""Contrat commandes ↔ paiements/livraisons : recalculer_montants (RG7),
enregistrer_changement_statut (RG15), et message de transition depuis « terminee »."""
from datetime import date

import pytest

from app.core.errors import Conflit, DonneesInvalides
from app.models.catalogue import TypeVetement
from app.models.client import Client
from app.models.commande import Commande, HistoriqueStatut, LigneCommande
from app.models.enums import ModePaiement, Role, Statut
from app.models.paiement import Paiement
from app.services import commandes_service as svc
from tests.conftest import creer_utilisateur


@pytest.fixture()
def accueil(db):
    return creer_utilisateur(db, Role.accueil, email="accueil-contrat@atelier.sn")


@pytest.fixture()
def commande(db, accueil) -> Commande:
    """2 boubous à 35 000 + 1 pantalon à 12 000, remise 5 000 → total 77 000. Aucun paiement."""
    cliente = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    boubou = TypeVetement(nom="Boubou", prix_base=35_000, delai_jours=10)
    pantalon = TypeVetement(nom="Pantalon", prix_base=12_000, delai_jours=4)
    db.add_all([cliente, boubou, pantalon])
    db.flush()
    cmd = Commande(
        numero="CMD-2026-00001", client_id=cliente.id, statut=Statut.en_attente,
        date_livraison_prevue=date(2026, 11, 20), remise=5_000, cree_par_id=accueil.id,
    )
    cmd.lignes.append(LigneCommande(type_vetement_id=boubou.id, quantite=2, prix_unitaire=35_000))
    cmd.lignes.append(LigneCommande(type_vetement_id=pantalon.id, quantite=1, prix_unitaire=12_000))
    db.add(cmd)
    db.commit()
    return cmd


def paiement(montant, auteur) -> Paiement:
    return Paiement(montant=montant, mode=ModePaiement.wave, enregistre_par_id=auteur.id)


# --- recalculer_montants (RG7) ------------------------------------------------


def test_recalculer_total_paye_solde(commande):
    svc.recalculer_montants(commande)
    assert (commande.montant_total, commande.montant_paye, commande.solde) == (77_000, 0, 77_000)


def test_recalculer_apres_un_paiement(db, commande, accueil):
    commande.paiements.append(paiement(20_000, accueil))
    svc.recalculer_montants(commande)
    db.commit()
    db.refresh(commande)
    assert (commande.montant_total, commande.montant_paye, commande.solde) == (77_000, 20_000, 57_000)


def test_recalculer_apres_annulation_d_un_paiement(db, commande, accueil):  # RG17 côté Sine
    p1, p2 = paiement(20_000, accueil), paiement(30_000, accueil)
    commande.paiements.extend([p1, p2])
    svc.recalculer_montants(commande)
    db.commit()

    commande.paiements.remove(p1)  # delete-orphan : le paiement est supprimé de la base au flush
    svc.recalculer_montants(commande)
    db.commit()
    db.refresh(commande)
    assert (commande.montant_paye, commande.solde) == (30_000, 47_000)
    assert db.get(Paiement, p1.id) is None


def test_commande_entierement_payee_solde_zero(commande, accueil):
    commande.paiements.append(paiement(77_000, accueil))
    svc.recalculer_montants(commande)
    assert commande.solde == 0


def test_remise_superieure_aux_prestations_422(commande):  # RG7
    commande.remise = 82_001
    with pytest.raises(DonneesInvalides, match="dépasse la somme des prestations"):
        svc.recalculer_montants(commande)


def test_remise_egale_aux_prestations_acceptee(commande):
    commande.remise = 82_000
    svc.recalculer_montants(commande)
    assert commande.montant_total == 0


def test_total_sous_le_deja_paye_409_sans_rien_modifier(commande, accueil):  # RG7
    commande.paiements.append(paiement(70_000, accueil))
    svc.recalculer_montants(commande)
    commande.remise = 10_000  # 82 000 − 10 000 = 72 000 ≥ 70 000 : accepté
    svc.recalculer_montants(commande)
    assert commande.montant_total == 72_000

    commande.remise = 20_000  # 62 000 < 70 000 déjà payés
    with pytest.raises(Conflit) as e:
        svc.recalculer_montants(commande)
    assert e.value.detail == (
        "Le total de la commande (62000 FCFA) ne peut pas être inférieur au montant déjà payé (70000 FCFA)."
    )
    assert (commande.montant_total, commande.montant_paye) == (72_000, 70_000)  # inchangés


# --- enregistrer_changement_statut (RG15) -------------------------------------


def test_premiere_ligne_a_la_creation_ancien_statut_vide(db, commande, accueil):
    ligne = svc.enregistrer_changement_statut(db, commande, Statut.en_attente, None, accueil)
    assert (ligne.ancien_statut, ligne.nouveau_statut) == (None, Statut.en_attente)
    assert ligne.id is not None and ligne.utilisateur_id == accueil.id


def test_changement_ecrit_ancien_nouveau_commentaire_utilisateur(db, commande, accueil):
    tailleur = creer_utilisateur(db, Role.tailleur, email="tailleur-contrat@atelier.sn")
    svc.enregistrer_changement_statut(db, commande, Statut.en_attente, None, accueil)
    ligne = svc.enregistrer_changement_statut(db, commande, Statut.en_coupe, "tissu reçu", tailleur)
    db.commit()

    assert commande.statut == Statut.en_coupe
    assert (ligne.ancien_statut, ligne.nouveau_statut) == (Statut.en_attente, Statut.en_coupe)
    assert (ligne.commentaire, ligne.utilisateur_id) == ("tissu reçu", tailleur.id)
    assert ligne.date_changement is not None


def test_historique_complet_dans_l_ordre(db, commande, accueil):  # annexe A, étape 5
    parcours = [Statut.en_attente, Statut.en_coupe, Statut.en_couture, Statut.essayage,
                Statut.retouches, Statut.essayage, Statut.terminee, Statut.livree]
    for statut in parcours:
        svc.enregistrer_changement_statut(db, commande, statut, None, accueil)
    db.commit()
    db.expire_all()

    lignes = db.get(Commande, commande.id).historique
    assert [(h.ancien_statut, h.nouveau_statut) for h in lignes] == list(zip([None] + parcours[:-1], parcours))
    assert db.query(HistoriqueStatut).count() == len(parcours)


def test_ne_verifie_pas_le_workflow_pour_la_livraison(db, commande, accueil):  # RG20 côté Sine
    commande.statut = Statut.terminee
    svc.enregistrer_changement_statut(db, commande, Statut.terminee, None, accueil)
    svc.enregistrer_changement_statut(db, commande, Statut.livree, "solde impayé autorisé", accueil)
    assert commande.statut == Statut.livree


# --- verifier_transition : message depuis « terminee » (PLAN_DE_TRAVAIL, section 7) ---


@pytest.mark.parametrize("nouveau", [Statut.annulee, Statut.en_couture, Statut.essayage])
def test_terminee_message_oriente_vers_la_livraison(nouveau):
    with pytest.raises(Conflit) as e:
        svc.verifier_transition(Statut.terminee, nouveau)
    assert e.value.detail == (
        f"Transition interdite : terminee → {nouveau.value}. "
        "Une commande terminée n'évolue que par la confirmation de livraison."
    )


@pytest.mark.parametrize("final", [Statut.livree, Statut.annulee])
def test_statuts_finaux_message_inchange(final):
    with pytest.raises(Conflit, match="Cette commande est à un statut final."):
        svc.verifier_transition(final, Statut.en_coupe)
