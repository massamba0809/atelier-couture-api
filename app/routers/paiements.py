"""Routes 32 à 34 : paiements. Responsable : Sine. RG16, RG17.

Chemins mixtes (/commandes/{id}/paiements et /paiements/{id}) : pas de prefix.

TODO : POST /commandes/{id}/paiements (accueil), GET /commandes/{id}/paiements,
DELETE /paiements/{id} (admin).
Logique : app/services/paiements_service.py. Après chaque paiement ou annulation,
recalculer commande.montant_paye (somme des paiements).
"""
from fastapi import APIRouter

router = APIRouter(tags=["Paiements"])
