FROM python:3.13-slim

# 1) ffmpeg (даёт ffmpeg и ffprobe), curl для healthcheck
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--reload"]
