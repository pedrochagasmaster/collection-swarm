FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src/ src/
COPY config/ config/

RUN pip install --no-cache-dir -e .

RUN mkdir -p output

EXPOSE 8000

CMD ["collection-swarm", "serve", "--host", "0.0.0.0"]
