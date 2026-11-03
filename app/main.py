from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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


_ORIGINES = {"body", "query", "path", "header", "cookie"}


def _nom_du_champ(loc: tuple) -> str:
    """("body", "lignes", 0, "quantite") -> "lignes.0.quantite"."""
    morceaux = [str(m) for m in loc if m not in _ORIGINES]
    return ".".join(morceaux) or "corps de la requête"


def _expliquer(erreur: dict) -> str:
    """Traduit les erreurs Pydantic courantes ; repli sur le message d'origine."""
    type_, ctx, msg = erreur["type"], erreur.get("ctx") or {}, erreur["msg"]
    if type_ == "missing":
        return "champ obligatoire"
    if type_ in ("string_too_short", "too_short"):
        unite = "caractère(s)" if type_ == "string_too_short" else "élément(s)"
        return f"trop court, minimum {ctx['min_length']} {unite}"
    if type_ in ("string_too_long", "too_long"):
        unite = "caractère(s)" if type_ == "string_too_long" else "élément(s)"
        return f"trop long, maximum {ctx['max_length']} {unite}"
    if type_ in ("int_parsing", "int_type", "int_from_float"):
        return "nombre entier invalide"
    if type_ in ("float_parsing", "float_type"):
        return "nombre invalide"
    if type_ == "greater_than":
        return f"doit être strictement supérieur à {ctx['gt']}"
    if type_ == "greater_than_equal":
        return f"doit être supérieur ou égal à {ctx['ge']}"
    if type_ == "less_than":
        return f"doit être strictement inférieur à {ctx['lt']}"
    if type_ == "less_than_equal":
        return f"doit être inférieur ou égal à {ctx['le']}"
    if type_ == "enum":
        return f"valeur non autorisée, valeurs possibles : {ctx['expected'].replace(' or ', ', ')}"
    if type_ == "value_error" and msg.startswith("value is not a valid email address"):
        return "adresse e-mail invalide"
    if type_ == "value_error":
        # Message d'un validateur maison (raise ValueError("...")) : déjà en français.
        return msg.removeprefix("Value error, ")
    return msg


@app.exception_handler(RequestValidationError)
async def erreur_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """422 au format imposé : {"detail": "Données invalides : champ : explication ; ..."}."""
    messages = [f"{_nom_du_champ(e['loc'])} : {_expliquer(e)}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Données invalides : " + " ; ".join(messages)})


# /health est hors préfixe
app.include_router(health.router)

API_PREFIX = "/api/v1"
for module in (
    auth, utilisateurs, clients, catalogue, mesures,
    commandes, paiements, livraisons, statistiques,
):
    app.include_router(module.router, prefix=API_PREFIX)
