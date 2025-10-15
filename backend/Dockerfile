FROM python:3.11-slim

WORKDIR /app

# ffmpeg para transcodificação do fluxo webm/opus -> PCM 16k
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir google-cloud-speech

COPY . .

EXPOSE 8000

CMD uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}

