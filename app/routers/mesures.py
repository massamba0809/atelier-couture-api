"""Routes 18 à 23 : mesures. Responsable : Sine. RG2, RG3, RG4.

Attention aux chemins : certaines routes sont sous /clients/{id}/mesures et
d'autres sous /mesures/{id}. Ce router n'a donc PAS de prefix : écrivez les
chemins complets. Déclarez /clients/{client_id}/mesures/derniere AVANT toute
route dynamique qui pourrait la masquer.

TODO : POST /clients/{id}/mesures (tailleur), GET /clients/{id}/mesures,
GET /clients/{id}/mesures/derniere, GET /mesures/{id}, PATCH /mesures/{id}
(tailleur), DELETE /mesures/{id} (tailleur).
Utiliser CHAMPS_MESURES (app/models/mesure.py) pour valider RG2.
"""
from fastapi import APIRouter

router = APIRouter(tags=["Mesures"])
