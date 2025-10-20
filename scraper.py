import time
import re
import html
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def _first_text_or_default(driver, by_sel_list, default=""):
    for by, sel in by_sel_list:
        try:
            el = driver.find_element(by, sel)
            txt = el.text.strip()
            if txt:
                return txt
        except:
            continue
    return default

def _wait_for_any(driver, selectors, timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        for by, sel in selectors:
            try:
                if driver.find_elements(by, sel):
                    return True
            except:
                continue
        time.sleep(0.5)
    return False

def _parse_srcset(srcset):
    """Retourne l'URL la plus pertinente depuis un srcset (préfère la plus haute résolution)."""
    if not srcset:
        return None
    s = html.unescape(srcset)
    parts = [p.strip() for p in s.split(',') if p.strip()]
    candidates = []
    for p in parts:
        segs = p.split()
        url = segs[0]
        score = 0
        if len(segs) > 1:
            m = re.match(r'(\d+)(w|x)?', segs[1])
            if m:
                try:
                    score = int(m.group(1))
                except:
                    score = 0
        candidates.append((score, html.unescape(url)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]

def _get_thumbnail_from_element(el):
    """
    Extraire l'URL de thumbnail en gérant les placeholders base64 (1x1 gif) et le lazy-loading.
    - Parcourt source/srcset/src/data-src/data-srcset...
    - Force scrollIntoView puis attend brièvement que le src réel soit chargé.
    """
    PLACEHOLDER_PATTERNS = ("data:image/gif;base64", "R0lGODlhAQABA")  # 1x1 gif common placeholder

    # obtenir driver via l'élément
    try:
        driver = el._parent
    except:
        driver = None

    # Scroller l'élément en vue pour déclencher le lazy-load
    try:
        if driver:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            time.sleep(0.35)
    except:
        pass

    # 1) <source srcset>
    try:
        sources = el.find_elements(By.CSS_SELECTOR, "picture source[srcset], source[srcset]")
        for s in sources:
            srcset = s.get_attribute("srcset") or s.get_attribute("data-srcset") or s.get_attribute("data-src")
            url = _parse_srcset(srcset)
            if url and not any(p in url for p in PLACEHOLDER_PATTERNS):
                return url
    except:
        pass

    # 2) <img> attributes
    try:
        imgs = el.find_elements(By.CSS_SELECTOR, "picture img, img")
        for img in imgs:
            # check srcset-like attrs first
            for a in ("srcset", "data-srcset"):
                val = img.get_attribute(a)
                if val:
                    url = _parse_srcset(val)
                    if url and not any(p in url for p in PLACEHOLDER_PATTERNS):
                        return url
            # then src-like attrs
            for a in ("src", "data-src", "data-original", "data-lazy", "data-image"):
                val = img.get_attribute(a)
                if val:
                    u = html.unescape(val)
                    if u and not any(p in u for p in PLACEHOLDER_PATTERNS):
                        return u
    except:
        pass

    # 3) attendre un peu pour que JS remplace le placeholder (vérifier quelques fois)
    try:
        imgs = el.find_elements(By.CSS_SELECTOR, "picture img, img")
        if imgs:
            img = imgs[0]
            for _ in range(8):  # ~2s total
                cur = img.get_attribute("src") or ""
                cur_un = html.unescape(cur)
                if cur_un and not any(p in cur_un for p in PLACEHOLDER_PATTERNS):
                    return cur_un
                curset = img.get_attribute("srcset") or img.get_attribute("data-srcset") or ""
                parsed = _parse_srcset(curset)
                if parsed and not any(p in parsed for p in PLACEHOLDER_PATTERNS):
                    return parsed
                time.sleep(0.25)
    except:
        pass

    # 4) fallback: parent data-* attributes
    try:
        parent = el
        for _ in range(3):
            for attr in ("data-src", "data-bg", "data-image", "data-thumbnail"):
                v = parent.get_attribute(attr)
                if v and not any(p in v for p in PLACEHOLDER_PATTERNS):
                    return html.unescape(v)
            parent = parent.find_element(By.XPATH, "..") or parent
    except:
        pass

    return ""  # aucun candidat valide trouvé

def _extract_between_guillemets(text):
    if not text:
        return ""
    t = html.unescape(text)
    m = re.search(r'«\s*(.*?)\s*»', t, flags=re.S)
    if m:
        return m.group(1).strip()
    m2 = re.search(r'“\s*(.*?)\s*”', t, flags=re.S)
    if m2:
        return m2.group(1).strip()
    # fallback: try to extract after colon if pattern like "... : « ... »" not present
    m3 = re.search(r':\s*["\']?\s*(.*?)\s*["\']?$', t, flags=re.S)
    if m3:
        return m3.group(1).strip()
    return t.strip()

def scrape_tiktok_account(account_url, num_videos=50, headless=True):
    options = Options()
    if headless:
        try:
            options.add_argument("--headless=new")
        except:
            options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(account_url)
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/video/"]')))
        time.sleep(2)

        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(),'Accept') or contains(text(),'ACCEPT') or contains(text(),'Autoriser')]")
            btn.click()
            time.sleep(1)
        except:
            pass

        scrolls = max(6, (num_videos // 12) + 2)
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        items = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        collected = []
        for el in items[:num_videos]:
            try:
                url = el.get_attribute("href")
                thumb = _get_thumbnail_from_element(el)
                views = ""
                try:
                    v = el.find_element(By.CSS_SELECTOR, 'strong[data-e2e*="views"], span[data-e2e*="views"]')
                    views = v.text.strip()
                except:
                    try:
                        views = el.get_attribute("aria-label") or ""
                    except:
                        views = ""
                collected.append({
                    "URL": url,
                    "Thumbnail": thumb,
                    "Views": views,
                    "Likes": "",
                    "Comments": "",
                    "Description": ""
                })
            except Exception as e:
                print("Collect base error:", e)
                continue

        likes_selectors = [(By.CSS_SELECTOR, 'strong[data-e2e="browse-like-count"]'),
                           (By.CSS_SELECTOR, 'strong[data-e2e*="like"]'),
                           (By.XPATH, "//strong[contains(@class,'like')]")]
        comments_selectors = [(By.CSS_SELECTOR, 'strong[data-e2e="browse-comment-count"]'),
                              (By.CSS_SELECTOR, 'strong[data-e2e*="comment"]'),
                              (By.XPATH, "//strong[contains(@class,'comment')]")]
        desc_selectors = [(By.CSS_SELECTOR, 'div[data-e2e="browse-video-desc"]'),
                          (By.CSS_SELECTOR, 'h1[data-e2e*="desc"]'),
                          (By.CSS_SELECTOR, 'meta[name="description"]')]

        for vid in collected:
            try:
                driver.get(vid["URL"])
                _wait_for_any(driver, likes_selectors + comments_selectors + desc_selectors, timeout=12)
                time.sleep(1.2)
                likes = _first_text_or_default(driver, likes_selectors, default="0")
                vid["Likes"] = re.sub(r'\s+', ' ', likes).strip() if likes else "0"
                comments = _first_text_or_default(driver, comments_selectors, default="0")
                vid["Comments"] = re.sub(r'\s+', ' ', comments).strip() if comments else "0"

                desc = ""
                for by, sel in desc_selectors:
                    try:
                        if by == By.CSS_SELECTOR and sel == 'meta[name="description"]':
                            meta = driver.find_element(By.CSS_SELECTOR, sel)
                            desc = meta.get_attribute("content") or ""
                            if desc:
                                break
                        else:
                            el = driver.find_element(by, sel)
                            txt = el.text.strip()
                            if txt:
                                desc = txt
                                break
                    except:
                        continue

                # keep only text between « ... » or “ ... ”
                cleaned = _extract_between_guillemets(desc)
                vid["Description"] = cleaned
                print("OK:", vid["URL"], "| L:", vid["Likes"], "C:", vid["Comments"], "D:", vid["Description"][:60])
            except Exception as e:
                print("Error visiting video", vid.get("URL"), e)
                continue

        return pd.DataFrame(collected)

    finally:
        driver.quit()

if __name__ == "__main__":
    df = scrape_tiktok_account("https://www.tiktok.com/@hugodecrypte", num_videos=20, headless=False)
    import os
    os.makedirs('output', exist_ok=True)
    df.to_csv('output/tiktok_videos.csv', index=False)
    print("Done")