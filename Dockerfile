FROM python:3.11.7-slim-bullseye as child_tracker_auth

RUN apt-get update -y && apt-get install -y pkg-config python3-dev default-libmysqlclient-dev build-essential

RUN pip install poetry==1.4.2

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry config virtualenvs.create false

RUN poetry install -n

COPY app/app /app/

RUN /bin/sh scripts/prestart.sh
