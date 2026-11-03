from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Genre


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), index=True)
    prenom: Mapped[str] = mapped_column(String(100), index=True)
    # Téléphone stocké NORMALISÉ (RG1) : unique.
    telephone: Mapped[str] = mapped_column(String(25), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    adresse: Mapped[str | None] = mapped_column(String(255))
    genre: Mapped[Genre | None] = mapped_column(Enum(Genre, native_enum=False, length=10))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    mesures: Mapped[list["Mesure"]] = relationship(  # noqa: F821
        back_populates="client", cascade="all, delete-orphan"
    )
    commandes: Mapped[list["Commande"]] = relationship(back_populates="client")  # noqa: F821
