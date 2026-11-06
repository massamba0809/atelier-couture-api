"""Règles de gestion des livraisons (routes 35 à 38).

Responsable : Sine. RG18, RG19, RG20.
Le passage à « livree » et la ligne d'historique passent par
commandes_service.enregistrer_changement_statut (contrat avec Massamba).
Cette fonction ne vérifie pas le workflow : c'est ici qu'on exige « terminee » (RG19).
"""
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Conflit, DonneesInvalides, Introuvable
from app.models.commande import Commande
from app.models.enums import ModeLivraison, Statut, StatutLivraison
from app.models.livraison import Livraison
from app.models.utilisateur import Utilisateur
from app.schemas.livraison import LivraisonConfirmation, LivraisonPlanification, LivraisonRead
from app.services.commandes_service import enregistrer_changement_statut
from app.services.pagination import paginer


def _obtenir_commande(db: Session, commande_id: int) -> Commande:
    commande = db.get(Commande, commande_id)
    if commande is None:
        raise Introuvable(f"Commande {commande_id} introuvable.")
    return commande


def planifier_livraison(db: Session, commande_id: int, donnees: LivraisonPlanification) -> Livraison:
    """Route 35 : RG18. Crée la livraison ou modifie l'existante (jamais de seconde livraison)."""
    commande = _obtenir_commande(db, commande_id)
    if commande.statut in (Statut.livree, Statut.annulee):
        raise Conflit(
            f"La commande {commande.numero} est « {commande.statut.value} » : "
            "sa livraison ne peut plus être planifiée."
        )
    if donnees.mode == ModeLivraison.domicile and not donnees.adresse:
        raise DonneesInvalides("Une livraison à domicile exige une adresse.")
    if donnees.date_prevue < commande.date_commande:
        raise DonneesInvalides(
            f"La date prévue ({donnees.date_prevue}) ne peut pas précéder "
            f"la date de commande ({commande.date_commande})."
        )

    livraison = commande.livraison
    if livraison is None:  # première planification
        livraison = Livraison()
        commande.livraison = livraison
    for champ, valeur in donnees.model_dump().items():  # replanifier = modifier l'existante
        setattr(livraison, champ, valeur)
    commande.date_livraison_prevue = donnees.date_prevue  # RG18
    db.flush()
    return livraison


def obtenir_livraison(db: Session, commande_id: int) -> Livraison:
    """Route 36 : 404 si aucune livraison n'est planifiée."""
    commande = _obtenir_commande(db, commande_id)
    if commande.livraison is None:
        raise Introuvable(f"Aucune livraison planifiée pour la commande {commande.numero}.")
    return commande.livraison


def confirmer_livraison(
    db: Session, commande_id: int, donnees: LivraisonConfirmation, utilisateur: Utilisateur
) -> Livraison:
    """Route 37 : RG19 (commande terminée et soldée, sauf autorisation) et RG20."""
    commande = _obtenir_commande(db, commande_id)
    if commande.statut != Statut.terminee:
        raise Conflit(
            f"Confirmation impossible : la commande {commande.numero} est au statut "
            f"« {commande.statut.value} », elle doit être « terminee »."
        )

    commentaire = None
    solde = commande.solde
    if solde > 0:
        if not donnees.autoriser_solde_impaye:
            raise Conflit(
                f"Confirmation impossible : il reste {solde} FCFA à payer. Encaissez le solde, "
                "ou envoyez autoriser_solde_impaye à true pour livrer quand même."
            )
        commentaire = f"Livré avec solde impayé de {solde} FCFA"  # RG19 : la dette reste visible

    jour = donnees.date_effective or date.today()
    livraison = commande.livraison
    if livraison is None:  # RG20 : sans planification, retrait à l'atelier
        livraison = Livraison(mode=ModeLivraison.retrait_atelier, date_prevue=jour)
        commande.livraison = livraison
    livraison.date_effective = jour
    livraison.statut = StatutLivraison.livree
    commande.date_livraison_reelle = jour
    enregistrer_changement_statut(db, commande, Statut.livree, commentaire, utilisateur)  # RG15, RG20
    return livraison


def _vers_tournee(livraison: Livraison) -> dict[str, Any]:
    commande = livraison.commande
    return {
        **LivraisonRead.model_validate(livraison).model_dump(),
        "numero_commande": commande.numero,
        "client_nom": f"{commande.client.prenom} {commande.client.nom}",
        "client_telephone": commande.client.telephone,
        "solde_commande": commande.solde,
    }


def lister_livraisons(
    db: Session,
    statut: StatutLivraison | None,
    date_min: date | None,
    date_max: date | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Route 38 : liste de tournée, triée par date prévue."""
    requete = select(Livraison)
    if statut is not None:
        requete = requete.where(Livraison.statut == statut)
    if date_min is not None:
        requete = requete.where(Livraison.date_prevue >= date_min)
    if date_max is not None:
        requete = requete.where(Livraison.date_prevue <= date_max)
    requete = requete.order_by(Livraison.date_prevue, Livraison.id)
    page = paginer(db, requete, limit, offset)
    page["items"] = [_vers_tournee(livraison) for livraison in page["items"]]
    return page
