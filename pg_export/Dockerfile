FROM public.ecr.aws/lambda/python:3.12

RUN pip install poetry

COPY pyproject.toml poetry.lock* ${LAMBDA_TASK_ROOT}/

ENV POETRY_VIRTUALENVS_CREATE=false

RUN poetry install --no-root

COPY lambda_pg_export.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda_pg_export.handler"]
