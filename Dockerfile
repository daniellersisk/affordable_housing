FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY app ./app
COPY tests ./tests
COPY alembic ./alembic
COPY alembic.ini ./
COPY entrypoint.sh ./
COPY migrate.sh ./
COPY README.md ./

RUN chmod +x entrypoint.sh migrate.sh

CMD ["bash", "entrypoint.sh"]
