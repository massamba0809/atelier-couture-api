from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import ErreurMetier
from app.routers import (
    auth,
    catalogue,
    clients,
    commandes,
    health,
    livraisons,
    mesures,
    paiements,
    statistiques,
    utilisateurs,
)

app = FastAPI(
    title="API Atelier de couture",
    description="Gestion des clients, mesures, commandes, paiements et livraisons.",
    version="1.0.0",
)


@app.exception_handler(ErreurMetier)
async def erreur_metier_handler(_: Request, exc: ErreurMetier) -> JSONResponse:
    """Format d'erreur imposé : {"detail": "message en français"}."""
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


# /health est hors préfixe
app.include_router(health.router)

API_PREFIX = "/api/v1"
for module in (
    auth, utilisateurs, clients, catalogue, mesures,
    commandes, paiements, livraisons, statistiques,
):
    app.include_router(module.router, prefix=API_PREFIX)
