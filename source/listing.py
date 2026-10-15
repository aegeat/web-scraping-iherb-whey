# -*- coding: utf-8 -*-
"""
Created on Sun Oct 26 17:39:48 2025

@author: aeget
"""

# source/listing.py
import time
import math
import re
from urllib.parse import urljoin, urlencode, urlparse, parse_qs, urlunparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCROLL_PAUSE = 0.6
SCROLL_MAX_LOOPS = 20

def smooth_scroll_to_bottom(driver, max_loops=SCROLL_MAX_LOOPS, pause=SCROLL_PAUSE):
    """Hace scroll incremental hasta estabilizar la altura o llegar al máximo de loops."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    loops = 0
    while loops < max_loops:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        loops += 1

def wait_listing_ready(driver, timeout=20):
    """
    Espera a que haya un grid de productos visible.
    Usamos un selector amplio: enlaces a /pr/ dentro del contenido.
    """
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/pr/']"))
    )

def get_total_pages_from_pagination(driver) -> int:
    """
    Obtiene el número total de páginas de la categoría.
    Estrategia:
      - buscar elementos de paginación con números
      - si no hay, devolver 1
    """
    # Muchos sitios usan una nav con links numerados. Probamos un selector amplio:
    candidates = driver.find_elements(By.CSS_SELECTOR, "a[href*='?p='], button[aria-label*='Page ']")
    page_nums = []
    for el in candidates:
        txt = (el.text or "").strip()
        # Page 2, '2', etc.
        m = re.search(r"\b(\d{1,3})\b", txt)
        if m:
            try:
                page_nums.append(int(m.group(1)))
            except:
                pass
        # También hay sitios que llevan el número en el href
        href = el.get_attribute("href") or ""
        m2 = re.search(r"[?&]p=(\d+)", href)
        if m2:
            try:
                page_nums.append(int(m2.group(1)))
            except:
                pass

    if page_nums:
        return max(page_nums)
    return 1

def build_page_url(base_url: str, page: int) -> str:
    """
    A partir de la URL base de categoría, fija el parámetro de paginación (?p=page).
    Conserva otros parámetros existentes.
    """
    parsed = urlparse(base_url)
    qs = parse_qs(parsed.query)
    qs["p"] = [str(page)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)
