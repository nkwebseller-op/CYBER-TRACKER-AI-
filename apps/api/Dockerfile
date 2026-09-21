FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python deps first so this layer caches across code changes.
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r apps/api/requirements.txt

# services/ lives above apps/api so we bring the whole tree in.
COPY services /app/services
COPY apps/api /app/apps/api

WORKDIR /app/apps/api

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
