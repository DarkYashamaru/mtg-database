from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class Archetype(Base):
    __tablename__ = "archetypes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    categories = relationship(
        "ArchetypeCategory",
        back_populates="archetype",
        cascade="all, delete-orphan"
    )

class ArchetypeCategory(Base):
    __tablename__ = "archetype_categories"
    __table_args__ = (
        UniqueConstraint(
            "archetype_id",
            "name",
            name="uq_archetype_category_name",
        ),
    )

    id = mapped_column(Integer, primary_key=True)
    archetype_id = mapped_column(ForeignKey("archetypes.id"))
    name = mapped_column(String)
    archetype = relationship("Archetype", back_populates="categories")
    tags = relationship("Tag", secondary="archetype_category_tags", back_populates="categories")

class ArchetypeCategoryTag(Base):
    __tablename__ = "archetype_category_tags"

    archetype_category_id = mapped_column(ForeignKey("archetype_categories.id"), primary_key=True)
    tag_id = mapped_column(ForeignKey("tags.id"), primary_key=True)