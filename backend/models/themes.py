from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    curated: Mapped[bool] = mapped_column(Boolean)

    categories = relationship(
        "ThemeCategory",
        back_populates="themes",
        cascade="all, delete-orphan"
    )

class ThemeCategory(Base):
    __tablename__ = "theme_categories"
    __table_args__ = (
        UniqueConstraint(
            "theme_id",
            "name",
            name="uq_theme_category_name",
        ),
    )

    id = mapped_column(Integer, primary_key=True)
    theme_id = mapped_column(ForeignKey("themes.id"))
    name = mapped_column(String)
    themes = relationship("Theme", back_populates="categories")
    tags = relationship("Tag", secondary="theme_category_tags", back_populates="categories")

class ThemeCategoryTag(Base):
    __tablename__ = "theme_category_tags"

    theme_category_id = mapped_column(ForeignKey("theme_categories.id"), primary_key=True)
    tag_id = mapped_column(ForeignKey("tags.id"), primary_key=True)


class CardTheme(Base):
    __tablename__ = "card_theme"

    oracle_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id", ondelete="CASCADE"), primary_key=True,)

    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True,)

    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0,)

    card = relationship("Card")
    theme = relationship("Theme")