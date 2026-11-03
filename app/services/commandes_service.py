"""Règles de gestion des commandes : le cœur du projet.

Ce module contient les fonctions PURES (sans base de données) dont dépendent
aussi les paiements et les livraisons. Elles sont déjà testées dans
tests/test_regles_commandes.py. Le reste (création, lignes, changement de
statut avec historique...) est à ajouter ici, par Massamba.
"""
from collections.abc import Iterable
from datetime import date, timedelta

from app.core.errors import Conflit
from app.models.enums import Statut

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
