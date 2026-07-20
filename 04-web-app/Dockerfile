FROM python:3.12-slim-bookworm

# exiftool enables image/audio metadata extraction (optional but cheap)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/md-converter

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/static ./static

ENV MD_WORKERS=2 \
    MD_RATE_PER_MINUTE=30 \
    MD_RATE_BURST=10

EXPOSE 8000
USER nobody
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
