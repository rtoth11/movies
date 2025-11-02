FROM public.ecr.aws/lambda/python:3.12

RUN pip install poetry

COPY pyproject.toml poetry.lock* ${LAMBDA_TASK_ROOT}/

RUN poetry install --no-root --without dev

COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["extract_scripts.handler"]
