"""Statistiques du patron (routes 39 à 43). Responsable : Sine.

Définitions (section 6 de l'énoncé) :
- chiffre d'affaires = total des commandes NON annulées, daté à la date de commande ;
- encaissé = total des paiements reçus, daté à la date de paiement
  (y compris ceux des commandes annulées : décision du binôme, voir README) ;
- reste à encaisser = somme des soldes des commandes non annulées.
"""
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DonneesInvalides
from app.models.catalogue import TypeVetement
from app.models.client import Client
from app.models.commande import Commande, LigneCommande
from app.models.enums import Statut, StatutLivraison
from app.models.livraison import Livraison
from app.models.paiement import Paiement
from app.schemas.statistique import Granularite
from app.services.commandes_service import STATUTS_FINAUX, est_en_retard
from app.services.pagination import paginer

NON_ANNULEE = Commande.statut != Statut.annulee


def periode_par_defaut(date_debut: date | None, date_fin: date | None) -> tuple[date, date]:
    """Par défaut : du 1er du mois à aujourd'hui. 422 si date_debut > date_fin."""
    aujourd_hui = date.today()
    debut = date_debut or aujourd_hui.replace(day=1)
    fin = date_fin or aujourd_hui
    if debut > fin:
        raise DonneesInvalides(
            f"La date de début ({debut}) ne peut pas être postérieure à la date de fin ({fin})."
        )
    return debut, fin


def _somme(db: Session, colonne, *conditions) -> int:
    """SUM(colonne) WHERE conditions ; 0 s'il n'y a aucune ligne."""
    return db.scalar(select(func.coalesce(func.sum(colonne), 0)).where(*conditions))


def tableau_de_bord(db: Session) -> dict[str, Any]:
    """Route 39."""
    aujourd_hui = date.today()
    debut_mois = aujourd_hui.replace(day=1)
    dans_le_mois = Commande.date_commande.between(debut_mois, aujourd_hui)

    par_statut = {statut: 0 for statut in Statut}  # tous les statuts, même à 0
    for statut, nombre in db.execute(
        select(Commande.statut, func.count(Commande.id)).group_by(Commande.statut)
    ):
        par_statut[statut] = nombre

    return {
        "chiffre_affaires_mois": _somme(db, Commande.montant_total, NON_ANNULEE, dans_le_mois),
        "encaisse_mois": _somme(
            db, Paiement.montant, Paiement.date_paiement.between(debut_mois, aujourd_hui)
        ),
        "nb_commandes_mois": db.scalar(
            select(func.count(Commande.id)).where(NON_ANNULEE, dans_le_mois)
        ),
        "reste_a_encaisser": _somme(
            db, Commande.montant_total - Commande.montant_paye, NON_ANNULEE
        ),
        "commandes_par_statut": par_statut,
        "nb_commandes_en_retard": db.scalar(  # RG11
            select(func.count(Commande.id)).where(
                Commande.statut.not_in(STATUTS_FINAUX),
                Commande.date_livraison_prevue < aujourd_hui,
            )
        ),
        "commandes_pretes_a_livrer": par_statut[Statut.terminee],
        "livraisons_du_jour": db.scalar(
            select(func.count(Livraison.id)).where(
                Livraison.date_prevue == aujourd_hui,
                Livraison.statut == StatutLivraison.planifiee,
            )
        ),
    }


def _cle(jour: date, granularite: Granularite) -> str:
    return jour.isoformat() if granularite == Granularite.jour else jour.strftime("%Y-%m")


def chiffre_affaires(
    db: Session, granularite: Granularite, date_debut: date | None, date_fin: date | None
) -> dict[str, Any]:
    """Route 40 : CA et encaissements par jour ou par mois ; seules les périodes actives."""
    debut, fin = periode_par_defaut(date_debut, date_fin)
    ca: dict[str, int] = defaultdict(int)
    encaisse: dict[str, int] = defaultdict(int)

    commandes = db.execute(
        select(Commande.date_commande, Commande.montant_total).where(
            NON_ANNULEE, Commande.date_commande.between(debut, fin)
        )
    )
    for jour, montant in commandes:
        ca[_cle(jour, granularite)] += montant

    paiements = db.execute(
        select(Paiement.date_paiement, Paiement.montant).where(
            Paiement.date_paiement.between(debut, fin)
        )
    )
    for jour, montant in paiements:
        encaisse[_cle(jour, granularite)] += montant

    periodes = [
        {"periode": cle, "chiffre_affaires": ca[cle], "encaisse": encaisse[cle]}
        for cle in sorted(set(ca) | set(encaisse))
    ]
    return {"granularite": granularite, "date_debut": debut, "date_fin": fin, "periodes": periodes}


def ventes_par_type(db: Session, date_debut: date | None, date_fin: date | None) -> list[dict[str, Any]]:
    """Route 41 : quantité vendue et CA avant remise par prestation, du plus élevé au plus faible."""
    debut, fin = periode_par_defaut(date_debut, date_fin)
    chiffre = func.sum(LigneCommande.quantite * LigneCommande.prix_unitaire)
    requete = (
        select(
            TypeVetement.id,
            TypeVetement.nom,
            func.sum(LigneCommande.quantite),
            chiffre,
        )
        .join(LigneCommande, LigneCommande.type_vetement_id == TypeVetement.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(TypeVetement.id, TypeVetement.nom)
        .order_by(chiffre.desc(), TypeVetement.nom)
    )
    return [
        {"type_vetement_id": id_, "nom": nom, "quantite_vendue": quantite, "chiffre_affaires": ca}
        for id_, nom, quantite, ca in db.execute(requete)
    ]


def top_clients(
    db: Session, date_debut: date | None, date_fin: date | None, limite: int
) -> list[dict[str, Any]]:
    """Route 42 : meilleurs clients de la période (commandes non annulées), par CA décroissant."""
    debut, fin = periode_par_defaut(date_debut, date_fin)
    chiffre = func.sum(Commande.montant_total)
    requete = (
        select(
            Client.id,
            Client.nom,
            Client.prenom,
            Client.telephone,
            func.count(Commande.id),
            chiffre,
            func.sum(Commande.montant_total - Commande.montant_paye),
        )
        .join(Commande, Commande.client_id == Client.id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(Client.id, Client.nom, Client.prenom, Client.telephone)
        .order_by(chiffre.desc(), Client.nom, Client.prenom)
        .limit(limite)
    )
    return [
        {
            "client_id": id_, "nom": nom, "prenom": prenom, "telephone": telephone,
            "nb_commandes": nb, "chiffre_affaires": ca, "solde_du": solde,
        }
        for id_, nom, prenom, telephone, nb, ca, solde in db.execute(requete)
    ]


def impayes(db: Session, limit: int, offset: int) -> dict[str, Any]:
    """Route 43 : commandes non annulées non soldées, la date prévue la plus proche d'abord."""
    aujourd_hui = date.today()
    requete = (
        select(Commande)
        .where(NON_ANNULEE, Commande.montant_total > Commande.montant_paye)
        .order_by(Commande.date_livraison_prevue, Commande.id)
    )
    page = paginer(db, requete, limit, offset)
    page["items"] = [
        {
            "id": c.id,
            "numero": c.numero,
            "client_id": c.client_id,
            "client_nom": f"{c.client.prenom} {c.client.nom}",
            "statut": c.statut,
            "date_livraison_prevue": c.date_livraison_prevue,
            "montant_total": c.montant_total,
            "montant_paye": c.montant_paye,
            "solde": c.solde,
            "en_retard": est_en_retard(c.statut, c.date_livraison_prevue, aujourd_hui),
        }
        for c in page["items"]
    ]
    return page
