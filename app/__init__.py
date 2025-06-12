from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from redis import Redis
import os

def create_app():
    app = Flask(__name__)

    # Настройка базы данных
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Инициализация движка SQLAlchemy
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    Session = sessionmaker(bind=engine)
    app.db_session = Session()
    app.db_engine = engine

    # Инициализация Redis
    app.redis = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))

    # Загрузка маршрутов
    from app import routes
    routes.init_app(app)

    # Загрузка моделей
    from app import models

    return app