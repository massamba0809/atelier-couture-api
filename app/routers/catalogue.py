"""Routes 14 à 17 : catalogue des prestations. Responsable : Massamba.

TODO : POST /catalogue (admin), GET /catalogue (actifs_seulement=true par défaut),
GET /catalogue/{id}, PATCH /catalogue/{id} (admin).
"""
from fastapi import APIRouter

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])
