from database.base import Base
from database.session import engine

# import all models
from models.card import *
from models.tag import *
from models.catalogs import *


def create_database():
    Base.metadata.create_all(bind=engine)