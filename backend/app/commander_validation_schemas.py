from pydantic import BaseModel, Field


COMMANDER_VALIDATION_MAX_SELECTIONS = 50_000


class CommanderSelectionRequest(BaseModel):
    oracle_ids: list[str] = Field(default_factory=list, max_length=2)


class CommanderValidationRequest(BaseModel):
    """Bound requests against abuse while supporting full-card-pool analysis."""

    selections: list[CommanderSelectionRequest] = Field(
        default_factory=list,
        max_length=COMMANDER_VALIDATION_MAX_SELECTIONS,
    )
