"""Routes 7 à 13 : clients. Responsable : Massamba. RG1, RG4.

TODO : POST /clients, GET /clients (q, genre, limit, offset), GET /clients/{id},
PATCH /clients/{id}, DELETE /clients/{id}, GET /clients/{id}/commandes,
GET /clients/{id}/resume.
Schémas : app/schemas/client.py (ClientCreate, ClientUpdate, ClientRead).
Logique : app/services/clients_service.py (normaliser_telephone existe déjà).
"""
from fastapi import APIRouter

router = APIRouter(prefix="/clients", tags=["Clients"])
