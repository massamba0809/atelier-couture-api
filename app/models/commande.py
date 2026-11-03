from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Statut


class Commande(Base):
    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # CMD-2026-00017 (RG5)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    mesure_id: Mapped[int | None] = mapped_column(ForeignKey("mesures.id"))
    statut: Mapped[Statut] = mapped_column(
        Enum(Statut, native_enum=False, length=20), default=Statut.en_attente, index=True
    )
    date_commande: Mapped[date] = mapped_column(Date, default=date.today)
    date_livraison_prevue: Mapped[date] = mapped_column(Date)
    date_livraison_reelle: Mapped[date | None] = mapped_column(Date)
    # Montants en FCFA (entiers), calculés par le serveur (RG7).
    remise: Mapped[int] = mapped_column(Integer, default=0)
    montant_total: Mapped[int] = mapped_column(Integer, default=0)
    montant_paye: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    cree_par_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="commandes")  # noqa: F821
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan"
    )
    historique: Mapped[list["HistoriqueStatut"]] = relationship(
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="HistoriqueStatut.date_changement",
    )
    paiements: Mapped[list["Paiement"]] = relationship(  # noqa: F821
        back_populates="commande", cascade="all, delete-orphan", order_by="Paiement.id"
    )
    livraison: Mapped["Livraison | None"] = relationship(  # noqa: F821
        back_populates="commande", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def solde(self) -> int:
        return self.montant_total - self.montant_paye


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id"), index=True)
    type_vetement_id: Mapped[int] = mapped_column(ForeignKey("types_vetement.id"))
    description: Mapped[str | None] = mapped_column(Text)
    quantite: Mapped[int] = mapped_column(Integer, default=1)
    prix_unitaire: Mapped[int] = mapped_column(Integer)

    commande: Mapped[Commande] = relationship(back_populates="lignes")
    type_vetement: Mapped["TypeVetement"] = relationship()  # noqa: F821


class HistoriqueStatut(Base):
    __tablename__ = "historique_statuts"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id"), index=True)
    # Vide à la création de la commande (RG15).
    ancien_statut: Mapped[Statut | None] = mapped_column(Enum(Statut, native_enum=False, length=20))
    nouveau_statut: Mapped[Statut] = mapped_column(Enum(Statut, native_enum=False, length=20))
    commentaire: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))
    date_changement: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commande: Mapped[Commande] = relationship(back_populates="historique")
