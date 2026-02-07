# Dottò Backend - Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy project and install from pyproject.toml (no dev dependencies)
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
