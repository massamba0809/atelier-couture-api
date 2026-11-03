"""Routes 3 à 6 : comptes utilisateurs (admin). Responsable : Massamba. RG21, RG24.

TODO : POST /utilisateurs, GET /utilisateurs, GET /utilisateurs/{id}, PATCH /utilisateurs/{id}
Schémas à créer dans app/schemas/utilisateur.py : UtilisateurCreate, UtilisateurUpdate, UtilisateurRead.
Logique dans app/services/utilisateurs_service.py.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])
