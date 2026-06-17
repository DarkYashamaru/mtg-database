from collections.abc import Mapping, Sequence

from pydantic import BaseModel
from models.card import Card
from models.tag import Tag
from models.themes import Theme, ThemeCategory, CardTheme, CommanderTheme
from sqlalchemy.orm import selectinload
from sqlalchemy import select


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
    description: str | None = None

class TagCollectionSchema(BaseModel):
    direct: list[TagSchema]
    inherited: list[TagSchema]

class KeywordSchema(BaseModel):
    #id: str
    label: str

class ColorSchema(BaseModel):
    symbol: str

class CardThemeMinimalSchema(BaseModel):
    theme_id: int
    name: str
    curated: bool
    score: int

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
    themes: list[CardThemeMinimalSchema]

class ThemeTagSchema(BaseModel):
    slug: str


class ThemeCategorySchema(BaseModel):
    id: int
    name: str
    tags: list[ThemeTagSchema]


class ThemeypeSchema(BaseModel):
    id: int
    name: str
    categories: list[ThemeCategorySchema]

class CardThemeSchema(BaseModel):
    oracle_id: str
    theme_id: int
    score: int
    name: str
    curated: bool

class CommanderThemeSchema(BaseModel):
    oracle_id: str
    theme_id: int
    score: int
    name: str
    curated: bool

def cardtheme_to_schema(cardtheme: CardTheme):
    return CardThemeSchema(oracle_id=cardtheme.oracle_id, theme_id=cardtheme.theme_id, score=cardtheme.score)

def commandertheme_to_schema(commanderTheme: CommanderTheme):
    return CardThemeSchema(oracle_id=commanderTheme.oracle_id, theme_id=commanderTheme.theme_id, score=commanderTheme.score)

def theme_tag_to_schema(tag: Tag) -> ThemeTagSchema:
    return ThemeTagSchema(
        slug=tag.slug
    )

def _tag_schemas(tags: Sequence[Tag]) -> list[TagSchema]:
    return [
        TagSchema(slug=tag.slug, description=tag.description)
        for tag in sorted(tags, key=lambda tag: tag.slug)
    ]

def card_to_schema(card: Card, inherited_tags_by_direct_id: Mapping[str, Sequence[Tag]] | None = None, themes_map = None,) -> CardSchema:
    direct_tags = [
        tagging.tag
        for tagging in card.taggings
        if tagging.tag is not None
    ]
    direct_tag_ids = {tag.id for tag in direct_tags}
    inherited_tags_by_direct_id = inherited_tags_by_direct_id or {}

    inherited_tags_by_id = {
        inherited_tag.id: inherited_tag
        for direct_tag in direct_tags
        for inherited_tag in inherited_tags_by_direct_id.get(direct_tag.id, [])
        if inherited_tag.id not in direct_tag_ids
    }

    card_themes = themes_map.get(card.oracle_id, [])

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

        themes=card_themes,

        tags=TagCollectionSchema(
            direct=_tag_schemas(direct_tags),
            inherited=_tag_schemas(list(inherited_tags_by_id.values())),
        ),

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


def tag_to_schema (tag: Tag):
    return TagSchema(slug=tag.slug, description=tag.description)

THEME_LOAD_OPTIONS = [
    selectinload(Theme.categories)
    .selectinload(ThemeCategory.tags)
]

def theme_to_schema(theme: Theme) -> ThemeypeSchema:

    return ThemeypeSchema(
        id=theme.id,
        name=theme.name,

        categories=[
            ThemeCategorySchema(
                id=category.id,
                name=category.name,

                tags=[
                    theme_tag_to_schema(tag)
                    for tag in sorted(
                        category.tags,
                        key=lambda t: t.label
                    )
                ]
            )
            for category in sorted(
                theme.categories,
                key=lambda c: c.name
            )
        ]
    )
