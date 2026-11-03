"""Routes 39 à 43 : statistiques (admin uniquement). Responsable : Sine.

TODO : GET /statistiques/tableau-de-bord, /statistiques/chiffre-affaires,
/statistiques/types-vetement, /statistiques/top-clients, /statistiques/impayes.
Tout le router est réservé à l'admin : dependencies=[Depends(require_roles())].
NB : les chemins exacts sont à vérifier dans l'énoncé (le PDF les coupe à la
ligne : tableau-de-bord, chiffre-affaires, types-vetement).
"""
from fastapi import APIRouter

router = APIRouter(prefix="/statistiques", tags=["Statistiques"])
