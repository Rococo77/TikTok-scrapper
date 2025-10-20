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
    if not srcset:
        return None
    parts = [p.strip() for p in srcset.split(',') if p.strip()]
    if not parts:
        return None
    first = parts[0].split()[0]
    return first

def _get_thumbnail_from_element(el):
    # Try picture > img, picture > source[srcset], then img
    try:
        pic_img = el.find_element(By.CSS_SELECTOR, "picture img")
        src = pic_img.get_attribute("src")
        if src:
            return src
    except:
        pass
    try:
        pic_source = el.find_element(By.CSS_SELECTOR, "picture source")
        srcset = pic_source.get_attribute("srcset")
        parsed = _parse_srcset(srcset)
        if parsed:
            return parsed
    except:
        pass
    try:
        img = el.find_element(By.TAG_NAME, "img")
        src = img.get_attribute("src")
        if src:
            return src
    except:
        pass
    return ""

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
    # fallback: if meta description contains pattern like "Vidéo TikTok ... : « ... »" try to find first occurrence
    m3 = re.search(r':\s*["\']?\s*(.*?)\s*["\']?$', t, flags=re.S)
    if m3:
        return m3.group(1).strip()
    return t.strip()

def scrape_tiktok_account(account_url, num_videos=50, headless=True):
    options = Options()
    if headless:
        # use newer headless argument if supported
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