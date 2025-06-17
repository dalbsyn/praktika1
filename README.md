# praktika1

## Подготовка среды

В корне репозитория требуется создать файл .env со следующим содержимым:

```dotenv
# Настройки подключения к базе данных
POSTGRES_DB=sample
POSTGRES_USER=postgres
POSTGRES_PASSWORD=123
POSTGRES_PORT=5432
POSTGRES_HOST=localhost

# Настройки подключения к другим сервисам
REDIS_PORT=6379
FLASK_APP_PORT=5000

# ЭТО НЕ ТРОГАТЬ
DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
REDIS_URL="redis://redis:${REDIS_PORT}/0"
```

Настройка самого приложения производится в `app/config.py`.

## Запуск приложения

```shell
docker-compose up
```