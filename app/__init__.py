from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from redis import Redis
import os

from app import config
from app.routes import init_app
from app.models import Base

engine = None
SessionLocal = None

def create_app():
    app = Flask(__name__)

    # Настройки приложения
    app.config.from_object(config)

    # Инициализация движка SQLAlchemy
    global engine, SessionLocal
    engine = create_engine(app.config['DATABASE_URL'], echo=True)
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['sqlalchemy_session'] = SessionLocal

    # Инициализация Redis
    app.redis = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))

    init_app(app)

    @app.teardown_appcontext
    def remove_session(exception=None):
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Безопасное получение фабрики сессий ---
        # Используем .get() для безопасного доступа, чтобы избежать KeyError
        db_session_factory = app.extensions.get('sqlalchemy_session')
        if db_session_factory:
            db_session_factory.remove()
            app.logger.debug("Сессия SQLAlchemy закрыта.")
        else:
            app.logger.warning("Фабрика сессий SQLAlchemy не найдена при завершении контекста.")

        if exception:
            app.logger.error(f"Контекст запроса завершился с ошибкой: {exception}")

    return app