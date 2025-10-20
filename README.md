# TikTok Scraper

Ce projet scrape les informations des vidéos d'un compte TikTok et les exporte dans un fichier CSV. Interface Streamlit pour configuration et affichage.

## Données extraites
- URL de la vidéo
- Description
- Thumbnail (URL)
- Nombre de vues
- Nombre de likes
- Nombre de commentaires

## Prérequis
- Python 3.9+ installé (pour développement local).
- Docker installé (pour conteneurisation).

## Installation et Lancement

### Développement local (Windows)
1. Créez un environnement virtuel : `python -m venv venv` puis `venv\Scripts\activate`.
2. Installez les dépendances : `pip install -r requirements.txt`.
3. Lancez l'interface Streamlit : `streamlit run app.py`.
4. Accédez à `http://localhost:8501` pour l'interface.

### Conteneurisation (Docker sur Linux)
1. Construisez l'image : `docker build -t tiktok-scraper .`
2. Lancez le conteneur : `docker run -p 8501:8501 -v /chemin/host/output:/app/output tiktok-scraper`
3. Accédez à `http://localhost:8501` pour l'interface Streamlit.

## Structure
- `scraper.py` : Fonction de scraping.
- `app.py` : Interface Streamlit.
- `requirements.txt` : Dépendances pour Windows (versions spécifiques pour debugging).
- `linux-requirements.txt` : Dépendances pour Docker/Linux (compatibilité OS).
- `Dockerfile` : Configuration Docker.
- `output/` : Répertoire pour les CSV (persistant via volume Docker).

## Notes
- Respectez les termes d'utilisation de TikTok.
- Testez localement sur Windows avant Docker pour détecter les erreurs de dépendances.
- Le CSV est sauvegardé dans `output/` (persistant hors conteneur).