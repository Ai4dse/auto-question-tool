FROM python:3.12-slim

# --- install build tools for bcrypt ---
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- install dependencies ---
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-4}"]
