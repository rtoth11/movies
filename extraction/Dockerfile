FROM public.ecr.aws/lambda/python:3.12

ARG DATABRICKS_MOVIE_DATA_VOLUME_PATH
ENV DATABRICKS_MOVIE_DATA_VOLUME_PATH=${DATABRICKS_MOVIE_DATA_VOLUME_PATH}

RUN pip install poetry

COPY pyproject.toml poetry.lock* ${LAMBDA_TASK_ROOT}/

ENV POETRY_VIRTUALENVS_CREATE=false

RUN poetry install --no-root --without dev

COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["extract_movie_data.handler"]
