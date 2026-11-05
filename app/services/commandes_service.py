"""Règles de gestion des commandes : le cœur du projet.

Ce module contient les fonctions PURES (sans base de données) dont dépendent
aussi les paiements et les livraisons, testées dans tests/test_regles_commandes.py,
puis les deux fonctions de CONTRAT utilisées par Sine (paiements, livraisons) :
recalculer_montants et enregistrer_changement_statut, testées dans
tests/test_commandes_contrat.py. Le reste (création, lignes...) est à ajouter ici.
"""
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import Conflit, DonneesInvalides
from app.models.commande import Commande, HistoriqueStatut
from app.models.enums import Statut
from app.models.utilisateur import Utilisateur

# Workflow des statuts (section 6 de l'énoncé).
TRANSITIONS: dict[Statut, set[Statut]] = {
    Statut.en_attente: {Statut.en_coupe, Statut.annulee},
    Statut.en_coupe: {Statut.en_couture, Statut.annulee},
    Statut.en_couture: {Statut.essayage, Statut.terminee, Statut.annulee},
    Statut.essayage: {Statut.retouches, Statut.terminee, Statut.annulee},
    Statut.retouches: {Statut.essayage, Statut.terminee, Statut.annulee},
    Statut.terminee: {Statut.livree},
    Statut.livree: set(),
    Statut.annulee: set(),
}

STATUTS_FINAUX = {Statut.livree, Statut.annulee}


def verifier_transition(actuel: Statut, nouveau: Statut) -> None:
    """Lève Conflit (409) si la demande de changement de statut est interdite.

    Utilisée par la route POST /commandes/{id}/statut (RG13). La confirmation
    de livraison pose « livree » directement, sans passer par ici.
    """
    if nouveau == actuel:
        raise Conflit(f"La commande est déjà au statut « {actuel.value} ».")
    if nouveau == Statut.livree:
        raise Conflit(
            "Le statut « livree » ne peut pas être posé directement : "
            "utilisez la confirmation de livraison."
        )
    if nouveau not in TRANSITIONS[actuel]:
        possibles = ", ".join(sorted(s.value for s in TRANSITIONS[actuel] - {Statut.livree}))
        if actuel == Statut.terminee:
            # « terminee » n'est pas un statut final : seule la livraison la fait évoluer.
            raise Conflit(
                f"Transition interdite : {actuel.value} → {nouveau.value}. "
                "Une commande terminée n'évolue que par la confirmation de livraison."
            )
        if not possibles:
            raise Conflit(
                f"Transition interdite : {actuel.value} → {nouveau.value}. "
                "Cette commande est à un statut final."
            )
        raise Conflit(
            f"Transition interdite : {actuel.value} → {nouveau.value}. "
            f"Statuts possibles : {possibles}"
        )


def calculer_total(lignes: Iterable[tuple[int, int]], remise: int = 0) -> int:
    """total = somme(quantité × prix_unitaire) − remise. `lignes` = (quantite, prix_unitaire)."""
    return sum(q * p for q, p in lignes) - remise


def calculer_solde(montant_total: int, montant_paye: int) -> int:
    """solde = total − payé."""
    return montant_total - montant_paye


def formater_numero(annee: int, commande_id: int) -> str:
    """RG5 : CMD-AAAA-NNNNN, par exemple CMD-2026-00017."""
    return f"CMD-{annee}-{commande_id:05d}"


def date_livraison_par_defaut(date_commande: date, delais_jours: Iterable[int]) -> date:
    """RG8 : date de commande + le plus long délai des prestations commandées."""
    return date_commande + timedelta(days=max(delais_jours))


def est_en_retard(statut: Statut, date_livraison_prevue: date | None, aujourd_hui: date) -> bool:
    """RG11 : date prévue dépassée et commande ni livrée ni annulée."""
    if statut in STATUTS_FINAUX or date_livraison_prevue is None:
        return False
    return date_livraison_prevue < aujourd_hui


# --- Contrat avec les paiements et les livraisons (Sine) ----------------------
# Signatures figées : prévenir l'autre AVANT de les changer (PLAN_DE_TRAVAIL.md, section 3).


def recalculer_montants(commande: Commande) -> None:
    """RG7 : recalcule montant_total et montant_paye à partir des lignes et des paiements.

    total = somme(quantité × prix unitaire) − remise ; payé = somme des paiements ;
    le solde (commande.solde) s'en déduit.

    Lit les collections commande.lignes et commande.paiements : ajouter ou retirer
    par ces listes (commande.paiements.append(p), commande.paiements.remove(p)),
    pas seulement avec db.add / db.delete, sinon le calcul ne les voit pas.

    Ne modifie rien si une règle est violée :
    - remise supérieure à la somme des prestations → DonneesInvalides (422) ;
    - total ramené sous le montant déjà payé → Conflit (409).
    """
    sous_total = calculer_total(((lg.quantite, lg.prix_unitaire) for lg in commande.lignes), 0)
    remise = commande.remise or 0
    if remise > sous_total:
        raise DonneesInvalides(
            f"La remise ({remise} FCFA) dépasse la somme des prestations ({sous_total} FCFA)."
        )
    total = sous_total - remise
    paye = sum(p.montant for p in commande.paiements)
    if total < paye:
        raise Conflit(
            f"Le total de la commande ({total} FCFA) ne peut pas être inférieur "
            f"au montant déjà payé ({paye} FCFA)."
        )
    commande.montant_total = total
    commande.montant_paye = paye


def enregistrer_changement_statut(
    db: Session,
    commande: Commande,
    nouveau: Statut,
    commentaire: str | None,
    utilisateur: Utilisateur,
) -> HistoriqueStatut:
    """RG15 : pose le nouveau statut et écrit la ligne d'historique correspondante.

    La première ligne d'une commande (à sa création) a un ancien statut vide.
    Ne vérifie PAS le workflow : la route 28 appelle verifier_transition avant,
    la confirmation de livraison (RG20) pose « livree » directement.
    """
    ancien = commande.statut if commande.historique else None
    ligne = HistoriqueStatut(
        ancien_statut=ancien,
        nouveau_statut=nouveau,
        commentaire=commentaire,
        utilisateur_id=utilisateur.id,
        # Heure Python plutôt que now() SQL : sous PostgreSQL, now() est la même
        # pour toute la transaction, ce qui mélangerait l'ordre de l'historique.
        date_changement=datetime.now(timezone.utc),
    )
    commande.statut = nouveau
    commande.historique.append(ligne)
    db.flush()
    return ligne
