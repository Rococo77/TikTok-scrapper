FROM python:3.13-slim

# Installer les dépendances système pour Selenium
RUN apt-get update && apt-get install -y wget gnupg && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    apt-get clean

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers
COPY linux-requirements.txt .
COPY scraper.py .
COPY app.py .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r linux-requirements.txt

# Créer un volume pour persister le CSV
VOLUME ["/app/output"]

# Commande par défaut
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]