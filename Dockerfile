FROM docker.io/library/python:3.13.4-slim-bookworm

WORKDIR /app

RUN pip install pipenv

COPY Pipfile* ./

RUN pipenv install --system --deploy --ignore-pipfile

COPY . .

EXPOSE 5000

CMD ["pipenv", "run", "flask", "run", "--host=0.0.0.0"]