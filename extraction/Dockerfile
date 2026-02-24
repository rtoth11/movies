FROM python:3.12-slim

ARG DATABRICKS_MOVIE_DATA_VOLUME_PATH
ENV DATABRICKS_MOVIE_DATA_VOLUME_PATH=${DATABRICKS_MOVIE_DATA_VOLUME_PATH}

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock* /app/

ENV POETRY_VIRTUALENVS_CREATE=false

RUN poetry install --no-root --without dev

COPY src/ /app/src/

CMD ["python", "src/extract_movie_data.py"]
