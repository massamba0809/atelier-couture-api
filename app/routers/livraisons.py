"""Routes 35 à 38 : livraisons. Responsable : Sine. RG18, RG19, RG20.

Chemins mixtes (/commandes/{id}/livraison et /livraisons) : pas de prefix.

TODO : PUT /commandes/{id}/livraison (accueil), GET /commandes/{id}/livraison,
POST /commandes/{id}/livraison/confirmer (accueil), GET /livraisons (tournée).
La confirmation pose le statut « livree » directement (RG20) et écrit dans
l'historique (RG15, et la mention si autoriser_solde_impaye, RG19).
"""
from fastapi import APIRouter

router = APIRouter(tags=["Livraisons"])
