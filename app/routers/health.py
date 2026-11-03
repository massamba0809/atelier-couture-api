"""Route 44 : GET /health (hors préfixe /api/v1)."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["Santé"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))  # vérifie que la base répond
    return {"status": "ok"}
