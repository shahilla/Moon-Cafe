# =============================================================================
# Moon Café Interlaken - Container-Image (Dockerfile)
# Praxisarbeit VICC - Shahilla Fazal
# =============================================================================

FROM python:3.12-slim
WORKDIR /app

# Abhängigkeiten zuerst installieren (nutzt den Docker-Cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Quellcode kopieren und mit Gunicorn auf Port 8000 starten
COPY . .
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
