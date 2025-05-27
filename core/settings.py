from sqlalchemy import URL
from dotenv import load_dotenv
from os import getenv

class Settings:
    load_dotenv(override=True)
    db_user = getenv('DB_USER')
    db_password = getenv('DB_PASSWORD')
    db_host = getenv('DB_HOST')
    db_port = getenv('DB_PORT')
    db_name = getenv('DB_NAME')
    '''
    В параметр port передается значение типа string, но вообще переменная
    ожидает типа integer, отчего, как минимум, LSP в VSCode показывает ошибку. 
    Ожидается, что пользователь в .env-файле точно введет значение нужного 
    порта правильно, то есть только целым числом. 
    Иначе - интерпретатор все равно выплюнет ошибку о неправильном типе.
    В общем, игнорируйте ошибку.
    '''
    
    url = 'postgresql+psycopg://{0}:{1}@{2}:{3}/{4}'.format(db_user, db_password, db_host, db_port, db_name)
