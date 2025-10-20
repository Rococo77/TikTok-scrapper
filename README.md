# TikTok Scraper

Outil minimal pour extraire les métadonnées des vidéos d'un compte TikTok (URL, description, miniature, vues, likes, commentaires) et les exporter en CSV. Interface utilisateur fournie via Streamlit.

## Fonctionnalités
- Scrape des vidéos d'un compte TikTok.
- Extraction : URL, description (texte entre « … » si présent), thumbnail, vues, likes, commentaires.
- Interface Streamlit pour lancer le scraping et télécharger le CSV.
- Volume Docker pour persister les exports (`/app/output`).

## Prérequis
- Python 3.12+ (développement local)
- Docker (exécution en conteneur)
- Chrome/Chromium (le Dockerfile installe Chrome pour Selenium)

## Quickstart — Développement local (Windows)
1. Créez et activez un venv :
   - cmd / PowerShell :
     python -m venv venv
     venv\Scripts\activate
2. Installez les dépendances :
   pip install -r requirements.txt
3. Lancez l'application :
   streamlit run app.py
4. Ouvrez :
   http://localhost:8501

## Quickstart — Docker (recommandé pour exécution isolée)
1. Construire l'image :
   docker build -t tiktok-scraper .
2. Créer le dossier `output` local (exemple Windows) :
   mkdir "D:\senscritique\TikTok-scrapper\output"
3. Lancer le conteneur (Windows) :
   docker run -d --name tiktok-scraper -p 8501:8501 -v "D:\senscritique\TikTok-scrapper\output:/app/output" tiktok-scraper
   (ou WSL2 : -v "/mnt/d/senscritique/TikTok-scrapper/output:/app/output")
4. Ouvrez dans votre navigateur :
   http://localhost:8501

Remarque : le log Streamlit affiche `URL: http://0.0.0.0:8501` — utilisez `http://localhost:8501` depuis votre machine hôte si le port est publié.

## Docker : conseils et dépannage rapide
- S'assurer d'avoir publié le port : `-p 8501:8501`.
- Vérifier que le conteneur tourne :
  docker ps
- Voir les logs :
  docker logs -f tiktok-scraper
- Si navigateur indique site inaccessible :
  - Vérifier mapping de ports : docker port tiktok-scraper
  - Sur Windows, vérifier firewall / règle pour le port 8501
  - Si vous utilisez Docker sur une machine distante, utilisez l'IP du serveur au lieu de `localhost`.

## Notes sur le scraping et fiabilité
- TikTok met fréquemment à jour son DOM; les sélecteurs peuvent nécessiter des ajustements.
- Le scraper utilise Selenium et navigue page par page : c'est fiable mais lent.
- Respectez les conditions d'utilisation de TikTok et limitez la fréquence des requêtes pour éviter le blocage.
- En cas de problèmes avec les miniatures (lazy-loading), exécutez en mode non-headless pour debug : dans `scraper.scrape_tiktok_account(..., headless=False)`.

## Fichiers importants
- `scraper.py` — logique de scraping.
- `app.py` — interface Streamlit.
- `requirements.txt` — dépendances pour développement Windows.
- `linux-requirements.txt` — dépendances pour Docker/Linux (plus légère).
- `Dockerfile` — image Docker (installe Chrome + dépendances).
- `output/` — dossier où sont écrits les CSV (monter en volume depuis l'hôte).

## Commandes utiles
- Rebuild image :
  docker build -t tiktok-scraper .
- Stop & remove conteneur :
  docker stop tiktok-scraper && docker rm tiktok-scraper
- Lancer conteneur (détaché) :
  docker run -d --name tiktok-scraper -p 8501:8501 -v "D:\senscritique\TikTok-scrapper\output:/app/output" tiktok-scraper

## Limitations & sécurité
- Ne pas utiliser pour collecter des données personnelles à grande échelle sans accord.
- Ne pas partager de clés/identifiants dans le code.
- Tester d'abord localement avant d'exécuter massivement en production.

Si vous voulez, j'ajoute une section pas-à-pas pour debugging (logs, capture d'écran via Selenium) ou j'adapte les instructions Docker à WSL2/Remote Docker.