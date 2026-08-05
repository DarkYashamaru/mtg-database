from database.base import Base
from database.session import engine

# import all models
from models.card import *
from models.tag import *
from models.archetype import *
from models.category import *
from models.catalogs import *
from models.themes import *


def create_database():
    Base.metadata.create_all(bind=engine)
