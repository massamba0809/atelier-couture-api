"""Routes 24 à 31 : commandes. Responsable : Massamba. RG5 à RG15.

TODO : POST /commandes, GET /commandes (filtres), GET /commandes/{id},
PATCH /commandes/{id}, POST /commandes/{id}/statut, GET /commandes/{id}/historique,
POST /commandes/{id}/lignes, DELETE /commandes/{id}/lignes/{ligne_id}.
Logique : app/services/commandes_service.py (workflow et montants déjà prêts).
"""
from fastapi import APIRouter

router = APIRouter(prefix="/commandes", tags=["Commandes"])
