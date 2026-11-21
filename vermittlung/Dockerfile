# KI-Vermittlung (MIN-344). Der Anthropic-Schlüssel kommt zur Laufzeit als Umgebungsvariable, nie ins Image.
FROM python:3.12-slim
# tzdata: zoneinfo reads Europe/Zurich from the system for the monthly budget (G98); the slim image may lack it.
# Pulls in only the time zone files, no Python package.
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10002 vermittlung && mkdir /data && chown vermittlung /data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
USER vermittlung
ENV VERMITTLUNG_DB=/data/vermittlung.sqlite VERMITTLUNG_HOST=0.0.0.0 VERMITTLUNG_PORT=8080 PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["python", "main.py"]
