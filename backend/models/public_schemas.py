from pydantic import BaseModel
from models.card import Card


class FaceSchema(BaseModel):
    name: str
    mana_cost: str | None
    oracle_text: str | None

    supertypes: list[str]
    card_types: list[str]
    subtypes: list[str]


class TagSchema(BaseModel):
    #id: str
    #label: str
    slug: str

class KeywordSchema(BaseModel):
    #id: str
    label: str


class CardSchema(BaseModel):
    oracle_id: str
    name: str
    cmc: float
    layout: str

    commander_legal: bool
    standard_legal: bool

    tags: list[TagSchema]
    faces: list[FaceSchema]
    keywords: list[KeywordSchema]

def card_to_schema(card: Card) -> CardSchema:
    return CardSchema(
        oracle_id=card.oracle_id,
        name=card.name,
        cmc=card.cmc,
        layout=card.layout,

        commander_legal=card.commander_legal,
        standard_legal=card.standard_legal,

        keywords=[
            KeywordSchema(
                label=t.keyword.value,
            )
            for t in card.keywords
        ],

        tags=[
            TagSchema(
                #id=t.tag.id,
                #label=t.tag.label,
                slug=t.tag.slug,
            )
            for t in card.taggings
        ],

        faces=[
            FaceSchema(
                name=face.name,
                mana_cost=face.mana_cost,
                oracle_text=face.oracle_text,

                supertypes=[
                    st.type.value
                    for st in face.supertypes
                ],

                card_types=[
                    ct.type.value
                    for ct in face.types
                ],

                subtypes=[
                    st.type.value
                    for st in face.subtypes
                ],
            )
            for face in card.faces
        ]
    )