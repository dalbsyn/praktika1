from core.models.base import Base
from core.models.clients import Clients
from sqlalchemy import create_engine

from core.settings import Settings

engine = create_engine(Settings.url, echo=True)
Base.metadata.create_all(engine)