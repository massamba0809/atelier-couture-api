"""Règles de gestion des paiements (routes 32 à 34).

Responsable : Sine. RG16, RG17.
Les montants de la commande sont recalculés par commandes_service.recalculer_montants
(contrat avec Massamba) : on ajoute et on retire les paiements PAR LA LISTE
commande.paiements, sinon le calcul ne les voit pas.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import Conflit, DonneesInvalides, Introuvable
from app.models.commande import Commande
from app.models.enums import Statut
from app.models.paiement import Paiement
from app.models.utilisateur import Utilisateur
from app.schemas.paiement import PaiementCreate
from app.services.commandes_service import recalculer_montants


def _obtenir_commande(db: Session, commande_id: int) -> Commande:
    commande = db.get(Commande, commande_id)
    if commande is None:
        raise Introuvable(f"Commande {commande_id} introuvable.")
    return commande


def enregistrer_paiement(
    db: Session, commande_id: int, donnees: PaiementCreate, auteur: Utilisateur
) -> Paiement:
    """Route 32 : RG16. Montant > 0 (schéma), refusé si la commande est annulée (409),
    date non future (422), montant au plus égal au solde restant (409)."""
    commande = _obtenir_commande(db, commande_id)
    if commande.statut == Statut.annulee:
        raise Conflit(f"Paiement refusé : la commande {commande.numero} est annulée.")

    date_paiement = donnees.date_paiement or date.today()
    if date_paiement > date.today():
        raise DonneesInvalides("La date de paiement ne peut pas être dans le futur.")

    solde = commande.solde
    if donnees.montant > solde:
        raise Conflit(
            f"Le paiement ({donnees.montant} FCFA) dépasse le solde restant ({solde} FCFA)."
        )

    paiement = Paiement(
        montant=donnees.montant,
        mode=donnees.mode,
        reference=donnees.reference,
        date_paiement=date_paiement,
        enregistre_par_id=auteur.id,
    )
    commande.paiements.append(paiement)  # par la liste : recalculer_montants le voit
    recalculer_montants(commande)
    db.flush()
    return paiement


def lister_paiements(db: Session, commande_id: int) -> list[Paiement]:
    """Route 33 : dans l'ordre de saisie (la relation est triée par id)."""
    return list(_obtenir_commande(db, commande_id).paiements)


def annuler_paiement(db: Session, paiement_id: int) -> None:
    """Route 34 : RG17, supprime le paiement et recalcule payé et solde de la commande."""
    paiement = db.get(Paiement, paiement_id)
    if paiement is None:
        raise Introuvable(f"Paiement {paiement_id} introuvable.")
    commande = paiement.commande
    commande.paiements.remove(paiement)  # delete-orphan : supprimé de la base au flush
    recalculer_montants(commande)
    db.flush()
