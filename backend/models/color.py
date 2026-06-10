from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Color(Base):
    """This table represents each mana color."""

    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(1), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"Color(id={self.id!r}, name={self.name!r}, symbol={self.symbol!r})"
