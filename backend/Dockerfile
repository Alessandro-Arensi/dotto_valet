# Dottò Backend - Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app

# Railway / Fly / similar inject $PORT; default 8000 for local docker.
ENV PORT=8000
EXPOSE 8000

# Shell form so $PORT expands at runtime
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}


