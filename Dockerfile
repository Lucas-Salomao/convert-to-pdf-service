FROM python:3.11-slim

# Instalar LibreOffice (Writer para DOCX, Impress para PPTX)
RUN apt-get update && apt-get install -y \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-common \
    fonts-liberation \
    fonts-dejavu \
    fonts-open-sans \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY app/ ./app/

# Expor porta
EXPOSE 8080

# Executar servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
