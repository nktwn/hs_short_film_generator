FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg git curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

EXPOSE 8000

CMD ["bash", "-lc", "\
  python3 manage.py makemigrations || true && \
  python3 manage.py migrate --noinput && \
  python3 manage.py runserver 0.0.0.0:8000 \
"]
