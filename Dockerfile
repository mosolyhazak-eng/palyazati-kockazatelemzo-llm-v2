# -------------------------------------------------------
# Pályázati kockázati API – Docker image
# -------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Rendszer függőségek (pdfplumber, pdfminer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Python függőségek
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Forráskód
COPY . .

# Log mappa
RUN mkdir -p logs models

# Adatbázis inicializálás és PDF feldolgozás (build-time opcionális)
# Ha runtime-ban akarod futtatni: CMD helyett entrypoint.sh

EXPOSE 8000

# API indítás
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
