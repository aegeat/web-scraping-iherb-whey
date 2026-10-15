# -*- coding: utf-8 -*-
"""
Created on Mon Nov  3 16:38:45 2025

@author: aeget
"""

# source/step1_list_all.py
import os, sys, time, pathlib
import pandas as pd
import re

from selenium.webdriver.common.by import By

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source.config import SEED_URL, USER_AGENT
from source.browser import get_driver, polite_sleep
from source.listing import (
    wait_listing_ready, smooth_scroll_to_bottom,
    get_total_pages_from_pagination, build_page_url
)


OUT_CSV = ROOT / "dataset" / "protein_listing_urls.csv"
MAX_PAGES = None  # pon un número si quieres limitar, None = todas

def parse_price_text(txt: str) -> float | None:
    """Convierte textos tipo '€29,50' a float."""
    if not txt:
        return None
    # Quitar espacios y símbolos, mantener dígitos, puntos y comas
    cleaned = re.sub(r"[^0-9,.\s]", "", txt).strip()
    # Normalizar coma decimal -> punto si parece formato europeo
    # Si hay coma y punto, asumimos punto como decimal. Si solo hay coma, reemplazar por punto.
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    # Tomar el último número con decimal si hay varios
    m_all = re.findall(r"\d+(?:\.\d+)?", cleaned)
    if not m_all:
        return None
    try:
        return float(m_all[-1])
    except:
        return None

def extract_cards(driver, max_cards=None):
    """
    Extrae una lista de dicts con info básica de cada producto del listing actual.
    Campos: name, brand (si se detecta), price, url
    """
    results = []
    # iHerb usa enlaces a detalle con /pr/ para productos
    card_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/pr/']")
    seen = set()
    for a in card_links:
        href = a.get_attribute("href") or ""
        if "/pr/" not in href:
            continue
        # Evitar duplicados por imágenes/títulos que apuntan al mismo href
        if href in seen:
            continue
        seen.add(href)

        # Intentamos obtener un texto "visible": título del producto suele venir en el enlace o en ascendentes
        name = (a.get_attribute("aria-label") or a.text or "").strip()
        if not name:
            # fallback: mirar en un contenedor padre el texto del título
            try:
                parent = a.find_element(By.XPATH, "./ancestor::div[1]")
                name = (parent.text or "").split("\n")[0].strip()
            except:
                name = ""

        # Para brand y price intentamos buscar en contenedores cercanos
        brand = ""
        price_val = None
        try:
            container = a.find_element(By.XPATH, "./ancestor::div[contains(@class,'product') or contains(@class,'card')][1]")
        except:
            container = None

        if container:
            # price
            # buscamos símbolos de moneda dentro del contenedor
            price_els = container.find_elements(By.XPATH, ".//*[contains(text(),'$') or contains(text(),'€') or contains(text(),'£')]")
            for pel in price_els:
                pv = parse_price_text(pel.text)
                if pv:
                    price_val = pv
                    break

            # brand: a veces aparece como primer span/link pequeño
            # probamos varios selectores típicos
            brand_candidates = container.find_elements(By.CSS_SELECTOR, "a[data-ga-brand], a[class*='brand'], span[class*='brand']")
            if brand_candidates:
                brand = (brand_candidates[0].text or "").strip()
            if not brand:
                # fallback: intentar deducir marca como primera palabra del nombre si está en MAYÚSCULAS
                fw = (name.split()[0] if name else "")
                if fw.isupper() and len(fw) >= 2:
                    brand = fw

        results.append(
            {
                "name": name,
                "brand": brand,
                "price": price_val,
                "url": href,
            }
        )
        if max_cards and len(results) >= max_cards:
            break
    return results


def main():
    driver = get_driver(headless=True, user_agent=USER_AGENT)
    try:
        # 1) Descubre cuántas páginas hay
        driver.get(build_page_url(SEED_URL, 1))
        wait_listing_ready(driver)
        total_pages = get_total_pages_from_pagination(driver) or 1
        if MAX_PAGES:
            total_pages = min(total_pages, MAX_PAGES)
        print(f"Total de páginas: {total_pages}")

        all_rows = []
        seen = set()

        for p in range(1, total_pages + 1):
            url = build_page_url(SEED_URL, p)
            print(f"- Página {p}/{total_pages}: {url}")
            driver.get(url)
            wait_listing_ready(driver)
            smooth_scroll_to_bottom(driver)

            rows = extract_cards(driver)  # [{'name','price','url','currency'}...]
            # deduplicar por URL
            for r in rows:
                u = r.get("url")
                if u and u not in seen:
                    seen.add(u)
                    all_rows.append(r)
            print(f"  + acumulado único: {len(all_rows)}")
            polite_sleep()

            # checkpoint cada 5 páginas
            if p % 5 == 0:
                tmp = pd.DataFrame(all_rows)
                OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
                tmp.to_csv(OUT_CSV, index=False, sep=';' , encoding='utf-8-sig')
                print(f"  [checkpoint] guardado parcial: {OUT_CSV}")

        df = pd.DataFrame(all_rows)
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT_CSV, index=False)
        print(f"\nListado completo guardado en: {OUT_CSV}")
        print(f"Total de productos únicos: {len(df)}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()

