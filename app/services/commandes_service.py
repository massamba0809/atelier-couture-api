"""Règles de gestion des commandes : le cœur du projet.

Ce module contient les fonctions PURES (sans base de données) dont dépendent
aussi les paiements et les livraisons, testées dans tests/test_regles_commandes.py,
puis les deux fonctions de CONTRAT utilisées par Sine (paiements, livraisons) :
recalculer_montants et enregistrer_changement_statut, testées dans
tests/test_commandes_contrat.py. Enfin, les routes 24 à 31.
"""
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, not_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Conflit, DonneesInvalides, Interdit, Introuvable
from app.models.commande import Commande, HistoriqueStatut, LigneCommande
from app.models.enums import Role, Statut
from app.models.mesure import Mesure
from app.models.utilisateur import Utilisateur
from app.schemas.commande import ChangementStatut, CommandeCreate, CommandeUpdate, LigneCreate
from app.services.catalogue_service import obtenir_prestation
from app.services.clients_service import obtenir_client
from app.services.mesures_service import dernieres_mesures
from app.services.pagination import paginer

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


# --- Routes 24 à 26 : création, liste, détail ---------------------------------


def obtenir_commande(db: Session, commande_id: int) -> Commande:
    commande = db.get(Commande, commande_id)
    if commande is None:
        raise Introuvable(f"Commande {commande_id} introuvable.")
    return commande


def _choisir_mesure(db: Session, client_id: int, mesure_id: int | None) -> int | None:
    """RG9 : mesures du client de la commande (422) ; par défaut ses dernières, s'il en a."""
    if mesure_id is None:
        derniere = dernieres_mesures(db, client_id)
        return derniere.id if derniere else None
    mesure = db.get(Mesure, mesure_id)
    if mesure is None or mesure.client_id != client_id:
        raise DonneesInvalides(
            f"La prise de mesures {mesure_id} n'appartient pas au client {client_id}."
        )
    return mesure.id


def _construire_ligne(db: Session, ligne: LigneCreate) -> tuple[LigneCommande, int]:
    """RG6 : prestation active (422 sinon), prix du catalogue par défaut. Renvoie (ligne, délai)."""
    prestation = obtenir_prestation(db, ligne.type_vetement_id)  # 404 si inconnue
    if not prestation.actif:
        raise DonneesInvalides(
            f"La prestation « {prestation.nom} » n'est plus proposée : elle ne peut pas être commandée."
        )
    prix = prestation.prix_base if ligne.prix_unitaire is None else ligne.prix_unitaire
    objet = LigneCommande(
        type_vetement_id=prestation.id, quantite=ligne.quantite,
        prix_unitaire=prix, description=ligne.description,
    )
    return objet, prestation.delai_jours


def creer_commande(db: Session, donnees: CommandeCreate, auteur: Utilisateur) -> Commande:
    """Route 24 : RG5, RG6, RG7, RG8, RG9, RG15. Statut initial en_attente."""
    client = obtenir_client(db, donnees.client_id)  # 404 si inconnu
    aujourd_hui = date.today()

    construites = [_construire_ligne(db, ligne) for ligne in donnees.lignes]  # RG6
    lignes = [ligne for ligne, _ in construites]
    delais = [delai for _, delai in construites]

    date_prevue = donnees.date_livraison_prevue or date_livraison_par_defaut(aujourd_hui, delais)  # RG8
    if date_prevue < aujourd_hui:
        raise DonneesInvalides(
            f"La date de livraison prévue ({date_prevue}) ne peut pas précéder la date de commande ({aujourd_hui})."
        )

    commande = Commande(
        numero=f"TMP-{uuid4().hex[:16]}",  # remplacé après le flush, une fois l'id connu (RG5)
        client_id=client.id,
        mesure_id=_choisir_mesure(db, client.id, donnees.mesure_id),  # RG9
        date_commande=aujourd_hui,
        date_livraison_prevue=date_prevue,
        remise=donnees.remise,
        notes=donnees.notes,
        cree_par_id=auteur.id,
    )
    commande.lignes.extend(lignes)
    recalculer_montants(commande)  # RG7 : 422 si la remise dépasse les prestations
    db.add(commande)
    db.flush()
    commande.numero = formater_numero(aujourd_hui.year, commande.id)  # RG5
    enregistrer_changement_statut(db, commande, Statut.en_attente, None, auteur)  # RG15
    return commande


# --- Routes 27 à 31 : modification, statut, historique, lignes ----------------


def _verifier_modifiable(commande: Commande) -> None:
    """RG12 : une commande livrée ou annulée n'est plus modifiable (409)."""
    if commande.statut in STATUTS_FINAUX:
        raise Conflit(
            f"La commande {commande.numero} est « {commande.statut.value} » : elle n'est plus modifiable."
        )


def _verifier_lignes_modifiables(commande: Commande) -> None:
    """RG10 (et RG12) : lignes modifiables seulement tant que la commande est « en_attente » (409)."""
    _verifier_modifiable(commande)
    if commande.statut != Statut.en_attente:
        raise Conflit(
            f"Les lignes de la commande {commande.numero} ne sont plus modifiables : "
            f"elle est « {commande.statut.value} » (seulement possible en « en_attente »)."
        )


def modifier_commande(db: Session, commande_id: int, donnees: CommandeUpdate) -> Commande:
    """Route 27 : mesure_id (RG9), date_livraison_prevue (RG8), remise (RG7), notes. RG12."""
    commande = obtenir_commande(db, commande_id)
    _verifier_modifiable(commande)
    champs = donnees.model_dump(exclude_unset=True)

    if champs.get("mesure_id") is not None:
        champs["mesure_id"] = _choisir_mesure(db, commande.client_id, champs["mesure_id"])  # RG9
    if "date_livraison_prevue" in champs and champs["date_livraison_prevue"] < commande.date_commande:
        raise DonneesInvalides(  # RG8
            f"La date de livraison prévue ({champs['date_livraison_prevue']}) ne peut pas précéder "
            f"la date de commande ({commande.date_commande})."
        )
    ancienne_remise = commande.remise
    for champ, valeur in champs.items():
        setattr(commande, champ, valeur)
    if "remise" in champs:
        try:
            recalculer_montants(commande)  # RG7 : 422 (remise > prestations) ou 409 (total < payé)
        except (DonneesInvalides, Conflit):
            commande.remise = ancienne_remise
            raise
    db.flush()
    return commande


def changer_statut(db: Session, commande_id: int, donnees: ChangementStatut, auteur: Utilisateur) -> Commande:
    """Route 28 : workflow (RG13), droits et commentaire d'annulation (RG14), historique (RG15)."""
    commande = obtenir_commande(db, commande_id)
    nouveau = donnees.statut
    if nouveau == Statut.annulee and auteur.role == Role.tailleur:
        raise Interdit("Le tailleur ne peut pas annuler une commande.")  # RG14
    verifier_transition(commande.statut, nouveau)  # RG13 (409, avec les statuts possibles)
    commentaire = donnees.commentaire or None
    if nouveau == Statut.annulee and commande.montant_paye > 0 and not commentaire:
        raise DonneesInvalides(  # RG14
            f"Cette commande a reçu {commande.montant_paye} FCFA : un commentaire est obligatoire "
            "pour l'annuler (remboursement, avoir...)."
        )
    enregistrer_changement_statut(db, commande, nouveau, commentaire, auteur)
    return commande


def lister_historique(db: Session, commande_id: int) -> list[HistoriqueStatut]:
    """Route 29 : ordre chronologique (id en cas d'égalité de date)."""
    commande = obtenir_commande(db, commande_id)
    requete = (
        select(HistoriqueStatut)
        .where(HistoriqueStatut.commande_id == commande.id)
        .order_by(HistoriqueStatut.date_changement, HistoriqueStatut.id)
    )
    return list(db.scalars(requete).all())


def ajouter_ligne(db: Session, commande_id: int, donnees: LigneCreate) -> Commande:
    """Route 30 : RG10, RG6, montants recalculés (RG7). La date prévue n'est pas modifiée."""
    commande = obtenir_commande(db, commande_id)
    _verifier_lignes_modifiables(commande)
    ligne, _ = _construire_ligne(db, donnees)
    commande.lignes.append(ligne)
    recalculer_montants(commande)  # ajouter une ligne ne peut que faire monter le total
    db.flush()
    return commande


def retirer_ligne(db: Session, commande_id: int, ligne_id: int) -> Commande:
    """Route 31 : RG10 (en_attente, au moins une ligne), 404 si la ligne n'est pas dans la commande."""
    commande = obtenir_commande(db, commande_id)
    _verifier_lignes_modifiables(commande)
    ligne = next((lg for lg in commande.lignes if lg.id == ligne_id), None)
    if ligne is None:
        raise Introuvable(f"Ligne {ligne_id} introuvable dans la commande {commande.numero}.")
    if len(commande.lignes) == 1:
        raise Conflit(
            f"Impossible de retirer la dernière ligne : la commande {commande.numero} "
            "doit garder au moins une prestation."
        )
    index = commande.lignes.index(ligne)
    commande.lignes.remove(ligne)  # delete-orphan : supprimée au flush
    try:
        recalculer_montants(commande)  # RG7 : 422 si la remise dépasse ce qui reste, 409 si total < payé
    except (DonneesInvalides, Conflit):
        commande.lignes.insert(index, ligne)
        raise
    db.flush()
    return commande


def _condition_en_retard(aujourd_hui: date):
    """RG11 en SQL, même définition que est_en_retard."""
    return and_(
        Commande.date_livraison_prevue < aujourd_hui,
        Commande.statut.not_in(list(STATUTS_FINAUX)),
    )


def lister_commandes(
    db: Session,
    *,
    statut: Statut | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    numero: str | None = None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Route 25 : la plus récente d'abord. date_min / date_max portent sur la date de commande."""
    requete = select(Commande).options(selectinload(Commande.client))
    if statut is not None:
        requete = requete.where(Commande.statut == statut)
    if client_id is not None:
        requete = requete.where(Commande.client_id == client_id)
    if en_retard is not None:
        condition = _condition_en_retard(date.today())
        requete = requete.where(condition if en_retard else not_(condition))
    if date_min is not None:
        requete = requete.where(Commande.date_commande >= date_min)
    if date_max is not None:
        requete = requete.where(Commande.date_commande <= date_max)
    if numero:
        requete = requete.where(Commande.numero.ilike(f"%{numero.strip()}%"))
    requete = requete.order_by(Commande.date_commande.desc(), Commande.id.desc())
    page = paginer(db, requete, limit, offset)
    page["items"] = [vue_resume(c) for c in page["items"]]
    return page


# --- Vues renvoyées par les routes (champs calculés) --------------------------


def vue_resume(commande: Commande) -> dict[str, Any]:
    """Champs de CommandeResume : ajoute client_nom, solde et en_retard (RG11)."""
    return {
        "id": commande.id,
        "numero": commande.numero,
        "client_id": commande.client_id,
        "client_nom": f"{commande.client.prenom} {commande.client.nom}",
        "statut": commande.statut,
        "date_commande": commande.date_commande,
        "date_livraison_prevue": commande.date_livraison_prevue,
        "montant_total": commande.montant_total,
        "montant_paye": commande.montant_paye,
        "solde": commande.solde,
        "en_retard": est_en_retard(commande.statut, commande.date_livraison_prevue, date.today()),
    }


def vue_detail(commande: Commande) -> dict[str, Any]:
    """Champs de CommandeRead : lignes (nom de la prestation, sous-total), paiements, livraison."""
    return {
        **vue_resume(commande),
        "mesure_id": commande.mesure_id,
        "date_livraison_reelle": commande.date_livraison_reelle,
        "remise": commande.remise,
        "notes": commande.notes,
        "cree_par_id": commande.cree_par_id,
        "created_at": commande.created_at,
        "updated_at": commande.updated_at,
        "lignes": [
            {
                "id": lg.id,
                "type_vetement_id": lg.type_vetement_id,
                "type_vetement_nom": lg.type_vetement.nom,
                "description": lg.description,
                "quantite": lg.quantite,
                "prix_unitaire": lg.prix_unitaire,
                "sous_total": lg.quantite * lg.prix_unitaire,
            }
            for lg in commande.lignes
        ],
        "paiements": list(commande.paiements),
        "livraison": commande.livraison,
    }
