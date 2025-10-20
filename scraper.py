import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def get_text_safe(driver, selectors, default=""):
    """
    Récupère de manière sûre le texte du premier sélecteur présent dans la page.

    Paramètres:
    - driver: WebDriver Selenium déjà positionné sur la page contenant l'élément.
    - selectors: liste de tuples (By, selector_string). L'ordre indique la priorité.
    - default: valeur retournée si aucun sélecteur n'est trouvé.

    Retour:
    - Chaîne de caractères correspondant au texte trouvé (stripé) ou la valeur `default`.

    Notes:
    - Utilise find_element pour obtenir le premier élément correspondant à chaque sélecteur.
    - Attrape et ignore les exceptions pour éviter d'interrompre le scraping.
    """
    for by, sel in selectors:
        try:
            return driver.find_element(by, sel).text.strip()
        except:
            continue
    return default


def get_thumbnail(element):
    """
    Extrait l'URL de la miniature (thumbnail) depuis un élément représentant une vidéo
    dans la liste de vidéos d'un compte TikTok.

    Paramètres:
    - element: WebElement correspondant au conteneur (<a> ou <div>) de la vidéo dans la page du compte.

    Retour:
    - URL de la miniature (chaîne) ou chaîne vide si non trouvée.

    Comportement:
    - Tente de scroller l'élément en vue pour déclencher le lazy-loading.
    - Parcourt les balises <img> et leurs attributs ("src", "data-src", "srcset") et
      renvoie la première URL valide différente d'un placeholder base64.
    - Pour `srcset`, prend la première URL listée (souvent la moins lourde), ce qui est suffisant
      pour récupérer une miniature fonctionnelle.
    - Ignore les placeholders de type "data:image/gif;base64" (1x1 gif).

    Limites:
    - Si la page utilise un chargement différé très long, l'image peut rester placeholder.
    - Comportement dépend du DOM actuel de TikTok; à adapter si TikTok change sa structure.
    """
    try:
        driver = element._parent
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
    except:
        pass

    try:
        imgs = element.find_elements(By.TAG_NAME, "img")
        for img in imgs:
            for attr in ["src", "data-src", "srcset"]:
                url = img.get_attribute(attr)
                if url and "data:image" not in url:
                    if attr == "srcset":
                        url = url.split(",")[0].split()[0]
                    return url
    except:
        pass

    return ""


def extract_description(text):
    """
    Extrait la description ciblée depuis un bloc de texte récupéré sur la page vidéo.

    Objectif spécifique: ne conserver que le texte situé entre guillemets français « ... »
    ou entre guillemets doubles " ... " si présent. Si aucun guillemet trouvé,
    retourne le texte nettoyé.

    Paramètres:
    - text: chaîne brute (ex. texte de la balise description ou meta description).

    Retour:
    - Chaîne contenant uniquement le texte extrait entre guillemets ou le texte nettoyé.

    Exemple:
    - input: 'Vidéo TikTok de ... : « Mon texte ici » ...'
      output: 'Mon texte ici'

    Notes:
    - Utilise une expression régulière tolerant les retours à la ligne (re.DOTALL).
    - Ne lève pas d'exception sur entrée None ou vide.
    """
    if not text:
        return ""

    match = re.search(r'[«"]\s*(.*?)\s*[»"]', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text.strip()


def scrape_tiktok_account(account_url, num_videos=50, headless=True):
    """
    Scrape les vidéos d'un compte TikTok et retourne un DataFrame Pandas.

    Paramètres:
    - account_url: URL complète du compte TikTok (ex. "https://www.tiktok.com/@hugodecrypte").
    - num_videos: nombre maximal de vidéos à récupérer (entier).
    - headless: bool pour exécuter Chrome en headless (utile en Docker).

    Retour:
    - pandas.DataFrame avec les colonnes: URL, Thumbnail, Views, Likes, Comments, Description.

    Comportement:
    - Lance un navigateur Chrome via webdriver-manager.
    - Charge la page du compte, accepte éventuellement le popup cookies (si présent).
    - Scroll pour charger suffisamment de vignettes vidéo.
    - Parcourt les liens de vidéos pour collecter URL, miniature et vues depuis la page principale.
    - Ensuite, visite chaque URL de vidéo pour récupérer Likes, Comments et Description.
    - Utilise des time.sleep simples pour la robustesse; WebDriverWait pourrait être ajouté
      pour des attentes plus précises si nécessaire.

    Gestion d'erreurs:
    - Les erreurs individuelles (ex. élément manquant, timeouts) sont capturées et affichées,
      le scraping continue pour les autres vidéos.
    - Le driver est toujours correctement fermé dans le bloc finally.

    Remarques:
    - Cette approche évite les stale element en collectant d'abord les URLs puis en visitant
      individuellement chaque page de vidéo.
    - Respectez les limitations de TikTok (rate limiting, conditions d'utilisation).
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(account_url)
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/video/"]'))
        )
        time.sleep(2)

        try:
            accept_btn = driver.find_element(
                By.XPATH,
                "//button[contains(text(),'Accept') or contains(text(),'Autoriser')]"
            )
            accept_btn.click()
            time.sleep(1)
        except:
            pass

        scrolls = max(6, num_videos // 12 + 2)
        for _ in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        video_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        videos = []

        for link in video_links[:num_videos]:
            try:
                url = link.get_attribute("href")
                thumb = get_thumbnail(link)

                views = ""
                try:
                    views_elem = link.find_element(
                        By.CSS_SELECTOR,
                        'strong[data-e2e*="views"]'
                    )
                    views = views_elem.text.strip()
                except:
                    pass

                videos.append({
                    "URL": url,
                    "Thumbnail": thumb,
                    "Views": views,
                    "Likes": "",
                    "Comments": "",
                    "Description": ""
                })
            except Exception as e:
                print(f"Erreur collecte vidéo: {e}")
                continue

        LIKES_SELECTORS = [
            (By.CSS_SELECTOR, 'strong[data-e2e="browse-like-count"]'),
            (By.CSS_SELECTOR, 'strong[data-e2e*="like"]')
        ]

        COMMENTS_SELECTORS = [
            (By.CSS_SELECTOR, 'strong[data-e2e="browse-comment-count"]'),
            (By.CSS_SELECTOR, 'strong[data-e2e*="comment"]')
        ]

        DESC_SELECTORS = [
            (By.CSS_SELECTOR, 'div[data-e2e="browse-video-desc"]'),
            (By.CSS_SELECTOR, 'h1[data-e2e*="desc"]')
        ]

        for i, video in enumerate(videos):
            try:
                print(f"Traitement {i+1}/{len(videos)}: {video['URL']}")
                driver.get(video["URL"])
                time.sleep(1.5)

                video["Likes"] = get_text_safe(driver, LIKES_SELECTORS, "0")
                video["Comments"] = get_text_safe(driver, COMMENTS_SELECTORS, "0")

                desc = get_text_safe(driver, DESC_SELECTORS, "")
                if not desc:
                    try:
                        meta = driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
                        desc = meta.get_attribute("content") or ""
                    except:
                        pass

                video["Description"] = extract_description(desc)

            except Exception as e:
                print(f"Erreur visite {video['URL']}: {e}")
                continue

        return pd.DataFrame(videos)

    finally:
        driver.quit()


if __name__ == "__main__":
    df = scrape_tiktok_account(
        "https://www.tiktok.com/@hugodecrypte",
        num_videos=20,
        headless=False
    )
    df.to_csv('output/tiktok_videos.csv', index=False)
    print("Terminé!")