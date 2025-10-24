FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY ./ /app/

RUN apt-get update && apt-get install -y gcc libpq-dev && \
    pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

