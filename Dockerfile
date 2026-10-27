FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY studio ./studio
ENV HOST=0.0.0.0 PORT=8000 DATA_DIR=/data
VOLUME /data
EXPOSE 8000
CMD ["python", "-m", "studio"]
