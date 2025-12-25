FROM python:3.11-slim

# Evitar interações durante a instalação (ex: EULA da Microsoft)
ENV DEBIAN_FRONTEND=noninteractive

# 1. Adicionar repositórios contrib e non-free para baixar fontes Microsoft
# 2. Instalar dependências, fontes e configurar Locale pt_BR
RUN echo "deb http://deb.debian.org/debian bookworm contrib non-free" >> /etc/apt/sources.list && \
    apt-get update && \
    # Aceitar licença EULA das fontes Microsoft automaticamente
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-common \
    # Fontes Essenciais para Fidelidade Microsoft
    ttf-mscorefonts-installer \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    fonts-liberation2 \
    fonts-noto-color-emoji \
    fonts-dejavu \
    fonts-open-sans \
    fonts-montserrat \
    # Utilitários de sistema
    locales \
    procps \
    && \
    # Configurar Locale para pt_BR (Garante A4 como padrão e margens corretas)
    sed -i -e 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=pt_BR.UTF-8 && \
    # Limpeza
    rm -rf /var/lib/apt/lists/*

# Definir variáveis de ambiente para Locale e Encoding
ENV LANG=pt_BR.UTF-8 \
    LANGUAGE=pt_BR:pt \
    LC_ALL=pt_BR.UTF-8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Criar usuário não-root por segurança (LibreOffice reclama se rodar como root)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
