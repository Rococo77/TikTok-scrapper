FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
        wget ca-certificates gnupg2 lsb-release apt-transport-https \
        fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libdbus-1-3 libdrm2 libxcomposite1 libxdamage1 libxrandr2 libx11-xcb1 \
        libxss1 libgbm1 libgtk-3-0 libxshmfence1 \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor >/usr/share/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >/etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*


COPY linux-requirements.txt .
COPY scraper.py .
COPY app.py .
COPY README.md .


RUN pip install --no-cache-dir -r linux-requirements.txt


VOLUME ["/app/output"]


EXPOSE 8501


CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]