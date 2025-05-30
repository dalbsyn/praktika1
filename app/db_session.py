from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database import Base
from app.settings import app_settings

engine = create_engine(app_settings.url, echo=True)

session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()
