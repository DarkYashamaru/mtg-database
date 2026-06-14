from pydantic import BaseModel
from models.card import Card
from models.tag import Tag


class FaceSchema(BaseModel):
    name: str
    mana_cost: str | None
    oracle_text: str | None

    supertypes: list[str]
    card_types: list[str]
    subtypes: list[str]
    small_image: str | None
    normal_image: str | None
    large_image: str | None


class TagSchema(BaseModel):
    slug: str

class TagCollectionSchema(BaseModel):
    direct: list[TagSchema]
    inherited: list[TagSchema]

class KeywordSchema(BaseModel):
    #id: str
    label: str

class ColorSchema(BaseModel):
    symbol: str


class CardSchema(BaseModel):
    oracle_id: str
    name: str
    cmc: float
    layout: str

    commander_legal: bool
    standard_legal: bool

    tags: TagCollectionSchema
    faces: list[FaceSchema]
    keywords: list[KeywordSchema]
    color_identity: list[ColorSchema]

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
            if t.keyword is not None
        ],

        color_identity=[
            ColorSchema(
                symbol=ci.color.symbol,
            )
            for ci in card.color_identity
            if ci.color is not None
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

                small_image=face.small_image,
                normal_image=face.normal_image,
                large_image=face.large_image,
            )
            for face in card.faces
        ]
    )