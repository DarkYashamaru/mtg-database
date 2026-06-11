from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.create_database import create_database
from database.session import get_db

from models.card import Card
from models.public_schemas import CardSchema, card_to_schema

from scripts.download_all_data import download_from_scryfall
from scripts.import_all import import_data_to_database


# --------------------------------------------------
# Startup / Shutdown
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting MTG Database API...")

    create_database()

    # Uncomment ONLY when you want to refresh data
    #download_data()
    #import_data()

    print("Startup complete")

    yield

    print("Shutting down...")

app = FastAPI(
    title="MTG Database API",
    version="0.1.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# Router
# --------------------------------------------------

router = APIRouter(prefix="/api")


@router.get(
    "/cards/{oracle_id}",
    response_model=CardSchema,
)
def get_card(
    oracle_id: str,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Card)
        .where(Card.oracle_id == oracle_id)
    )

    card = db.execute(stmt).scalar_one_or_none()

    if card is None:
        raise HTTPException(
            status_code=404,
            detail="Card not found",
        )

    return card_to_schema(card)


# Register router
app.include_router(router)


# --------------------------------------------------
# Data management helpers
# --------------------------------------------------

def download_data():
    print("Downloading bulk data from Scryfall...")
    download_from_scryfall()
    print("Download complete")


def import_data():
    print("Importing data into database...")
    import_data_to_database()
    print("Import complete")


# --------------------------------------------------
# Local development entrypoint
# --------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )