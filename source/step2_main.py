# -*- coding: utf-8 -*-
"""
Created on Sat Nov  1 18:08:30 2025

@author: aeget
"""

# source/step2_main.py
import os, sys, re, time, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from source.browser import get_driver, polite_sleep
from source.detail import (
    extract_leucine_from_text,
    guess_net_weight_from_title,
    extract_glutamine_from_text,           
    extract_glutamic_acid_from_text,       
)
from source.nutrition import extract_all_nutrients

LISTING_CSV = ROOT / "dataset" / "protein_listing_urls.csv"
OUT_CSV     = ROOT / "dataset" / "protein_details.csv"

DUMP_FIRST_N = 1  # 0 para desactivar

print("--------ATENCIÓN-------\nEste script puede tardar en ejecutarse hasta 12 horas")
print("Se puede ejecutar una prueba con pocos productos editando la variable 'urls' dentro de la función 'main'")
print("----------------------\n")
def dismiss_popups_if_any(driver):
    for sel, how in [
        ("button#onetrust-accept-btn-handler", By.CSS_SELECTOR),
        ("button[aria-label='Close']", By.CSS_SELECTOR),
        ("//*[@aria-label='Close']", By.XPATH),
    ]:
        try:
            driver.find_element(how, sel).click()
            time.sleep(0.3)
        except:
            pass

def get_visible_text(driver) -> str:
    try:
        txt = driver.execute_script(
            "return document.body && document.body.innerText ? document.body.innerText : ''"
        ) or ""
    except:
        txt = ""
    if not txt:
        try:
            txt = driver.find_element(By.TAG_NAME, "body").text or ""
        except:
            txt = ""
    return txt

def _norm_eur(s: str) -> float | None:
    # Normaliza distintos formatos: "1.234,56" -> 1234.56 ; "106.13" -> 106.13
    if not s:
        return None
    s = s.strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return None

def parse_price_eur(visible_text: str) -> float | None:
    """
    Regla 1: precio de 'One-off purchase' (preferido).
    Regla 2: usar 'Package quantity: XXX g' y tomar el precio asociado (siguiente '€' tras esa opción).
    Filtros: ignorar 'delivery', 'free', 'serving', 'autoship', etc.
    """
    txt = visible_text

    # --- Regla 1: 'One-off purchase' ---
    m = re.search(r"One[-\s]*off\s*purchase.*?([0-9][\d\.,]+)\s*€", txt, flags=re.I | re.S)
    if m:
        val = _norm_eur(m.group(1))
        if val is not None:
            return val

    # --- Regla 2: 'Package quantity: XXX g' ---
    sel = re.search(r"Package\s+quantity\s*:\s*([0-9][\d\.,]*)\s*g", txt, flags=re.I)
    if sel:
        grams = sel.group(1)
        # Buscamos el primer bloque que enumera opciones y precios
        # y tomamos el primer precio que siga a la opción seleccionada
        # Ejemplo en tu dump:
        # Package quantity: 453 g
        # 453 g
        # 29,48 €
        # 907 g
        # 50,54 €
        # ...
        # Creamos una ventana desde el inicio del primer "Package quantity:"
        start = sel.start()
        window = txt[start : start + 4000]  # suficiente
        # Encontrar la línea con la cantidad seleccionada sola (p.ej. "453 g")
        m_qty = re.search(rf"\b{re.escape(grams)}\s*g\b", window, flags=re.I)
        if m_qty:
            # Buscar el primer "€" DESPUÉS de la cantidad seleccionada
            after = window[m_qty.end():]
            # Itera precios y aplica filtros
            for px in re.finditer(r"([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})\s*€", after):
                span = after[max(0, px.start() - 25) : px.end() + 25].lower()
                if any(bad in span for bad in ["delivery", "free", "/serv", "autoship", "per ", "serving"]):
                    continue
                val = _norm_eur(px.group(1))
                if val is not None:
                    return val

    # --- Último recurso: primer precio en € razonable con filtros globales ---
    for m2 in re.finditer(r"([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})\s*€", txt):
        span = txt[max(0, m2.start() - 30) : m2.end() + 30].lower()
        if any(bad in span for bad in ["delivery", "free", "/serv", "autoship", "per ", "serving"]):
            continue
        val = _norm_eur(m2.group(1))
        if val is not None:
            return val

    return None

def _norm_int(num_str: str) -> int | None:
    if not num_str:
        return None
    s = num_str.strip()
    # normaliza 5,000 o 5.000 -> 5000
    s = s.replace(",", "").replace(".", "")
    try:
        return int(s)
    except:
        return None

def parse_product_rankings(visible_text: str) -> dict:
    """
    Solo admite estas categorías exactas (insensible a mayúsculas):
      Whey Protein, Whey Protein Isolate, Protein, Sport, Supplements
    """
    allowed = {
        "whey protein": "rank_whey_protein",
        "whey protein isolate": "rank_whey_protein_isolate",
        "protein": "rank_protein",
        "sport": "rank_sport",
        "supplements": "rank_supplements",
    }
    out = {}

    m = re.search(r"Product\s+rankings\s*:", visible_text, flags=re.I)
    if not m:
        return out

    # Ventana corta tras el ancla para no “comernos” otras secciones (“Autoship & Save”, etc.)
    block = visible_text[m.start(): m.start() + 600]

    # Coincidencias tipo: "#10 in Sport"
    for m2 in re.finditer(r"#\s*(\d+)\s+in\s+([A-Za-z][A-Za-z\s&\-]+)", block, flags=re.I):
        rank = _norm_int(m2.group(1))
        cat_raw = m2.group(2).strip().lower()
        # normaliza espacios múltiples
        cat_norm = re.sub(r"\s+", " ", cat_raw)
        if cat_norm in allowed and rank is not None:
            out[allowed[cat_norm]] = rank

    return out

def parse_recent_sales_30d(visible_text: str) -> dict:
    m = re.search(r"([\d.,]+)(\+)?\s*sold\s+in\s+30\s*days", visible_text, flags=re.I)
    if not m:
        return {"sold_30d": None}
    num = _norm_int(m.group(1))
    return {"sold_30d": num}

def parse_rating_reviews(visible_text: str) -> dict:
    """
    Intenta extraer:
      - rating: float (0.0–5.0)
      - reviews_count: int
    Usa varias heurísticas comunes en iHerb y evita el footer 'Store Reviews'.
    """
    txt = visible_text

    # ---- Caso 1: "4.7 Based on 38,215 ratings"
    m = re.search(
        r"\b([0-5](?:\.\d)?)\b\s*(?:\n|\s)*Based\s+on\s+([\d.,]+)\s*(?:ratings|reviews)",
        txt, flags=re.I
    )
    if m:
        return {
            "rating": float(m.group(1)),
            "reviews_count": _norm_int(m.group(2))
        }

    # ---- Caso 2: "Based on 38,215 ratings" (sin rating visible inmediato)
    m = re.search(
        r"Based\s+on\s+([\d.,]+)\s*(?:ratings|reviews)",
        txt, flags=re.I
    )
    if m:
        # rating podría estar en la línea anterior; intentamos capturar un float 0–5 en ventana previa
        start = max(0, m.start() - 40)
        window = txt[start:m.start()]
        m2 = re.search(r"\b([0-5](?:\.\d)?)\b", window)
        rating = float(m2.group(1)) if m2 else None
        return {
            "rating": rating,
            "reviews_count": _norm_int(m.group(1))
        }

    # ---- Caso 3: "4.7  \n  38,253 \n Reviews"
    # buscamos 'N Reviews' primero y luego un float 0–5 cercano antes
    m = re.search(r"\b([\d.,]+)\s*(?:Reviews|ratings)\b", txt, flags=re.I)
    if m and "store reviews" not in txt[m.start()-20:m.end()+20].lower():
        reviews = _norm_int(m.group(1))
        # ventana previa para encontrar el rating
        start = max(0, m.start() - 40)
        window = txt[start:m.start()]
        m2 = re.search(r"\b([0-5](?:\.\d)?)\b", window)
        rating = float(m2.group(1)) if m2 else None
        return {"rating": rating, "reviews_count": reviews}

    # ---- Último recurso: una línea tipo '4.7' seguida pocas líneas después de 'Based on' o 'Reviews'
    for m in re.finditer(r"\b([0-5](?:\.\d)?)\b", txt):
        around = txt[m.end(): m.end()+100]
        if re.search(r"(Based\s+on|Reviews|ratings)", around, flags=re.I):
            return {"rating": float(m.group(1)), "reviews_count": None}

    return {"rating": None, "reviews_count": None}


def parse_detail(driver, url: str, *, dump_index: int | None = None) -> dict:
    driver.get(url)
    polite_sleep()
    dismiss_popups_if_any(driver)
    try:
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
    except:
        pass

    visible_text = get_visible_text(driver)

    # Dump de diagnóstico (solo la primera URL)
    if dump_index is not None and dump_index < DUMP_FIRST_N:
        out_txt = ROOT / "dataset" / f"debug_visible_text_{dump_index+1}.txt"
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        


    # Título (para peso neto)
    try:
        title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
    except:
        try:
            title = driver.find_element(By.CSS_SELECTOR, "h2").text.strip()
        except:
            title = ""

    # --- Nutrición (todos los campos amount/serving) ---
    nut = extract_all_nutrients(visible_text)


    # --- Leucina (si aparece en texto) ---
    leucine_g = extract_leucine_from_text(visible_text)

    # --- Ingredientes (línea simple) ---
    ingredients_text = None
    m_ing = re.search(r"(?:^|\n)\s*(Other\s+Ingredients|Ingredients)\s*[:\-]?\s*(.+)", visible_text, flags=re.I)
    if m_ing:
        ingredients_text = m_ing.group(2).strip()

    # --- Peso neto desde título ---
    net_weight_g = guess_net_weight_from_title(title)

    # --- Precio (EUR) ---
    price_eur = parse_price_eur(visible_text)
    # --- Rankings y ventas 30d ---
    
    ranks = parse_product_rankings(visible_text)
    sales = parse_recent_sales_30d(visible_text)
    glutamine_g = extract_glutamine_from_text(visible_text)
    glutamic_acid_g = extract_glutamic_acid_from_text(visible_text)
    
    # --- Rating y nº de reseñas ---
    rr = parse_rating_reviews(visible_text)
    # --- Tamaño seleccionado (opcional, útil para €/100g) ---
    selected_size_g = None
    m_sel = re.search(r"Package\s+quantity\s*:\s*([0-9][\d\.,]*)\s*g", visible_text, flags=re.I)
    if m_sel:
        selected_size_g = _norm_eur(m_sel.group(1))
    record = {
        "title": title,
        "url": url,
        "net_weight_g": net_weight_g,
        "selected_size_g": selected_size_g,
        "ingredients_text": ingredients_text,
        "leucine_g_per_serving": leucine_g,
        "glutamine_g_per_serving": glutamine_g,          
        "glutamic_acid_g_per_serving": glutamic_acid_g,  
        "price_eur": price_eur,
        "rating": rr.get("rating"),
        "reviews_count": rr.get("reviews_count"),
    }
    # Nutrición detallada
    record.update(nut)
    # Rankings y ventas 30d
    record.update(ranks)
    record.update(sales)
    return record




def main():
    df = pd.read_csv(LISTING_CSV)
    urls = df["url"].dropna().unique().tolist()
    print(f"Probando {len(urls)} productos...")

    driver = get_driver(headless=False)
    rows = []
    try:
        for i, url in enumerate(urls, start=1):
            print(f"{i:02d}/{len(urls)}: {url}")
            try:
                rec = parse_detail(driver, url, dump_index=i-1)
            except Exception as e:
                rec = {"url": url, "error": str(e)}
            rows.append(rec)
            polite_sleep()
    finally:
        driver.quit()

    out_df = pd.DataFrame(rows)

    # ====== SELECCIÓN ESTRICTA DE COLUMNAS A EXPORTAR ======
    EXPORT_COLS = [
        # básicos
        "title", "url", "price_eur",
        # tamaños/pesos
        "net_weight_g",
        # nutrición
        "serving_size_text", "servings",
        "calories_kcal", "total_fat_g", "saturated_fat_g", "trans_fat_g",
        "cholesterol_mg", "sodium_mg", "total_carbohydrates_g", "dietary_fiber_g",
        "total_sugars_g", "added_sugars_g", "protein_g",
        "vitamin_d_mcg", "calcium_mg", "iron_mg", "potassium_mg",
        # amino/ingredientes
        "leucine_g_per_serving", "glutamine_g_per_serving", "glutamic_acid_g_per_serving", "ingredients_text",
        # rankings y ventas (SOLO los que te interesan)
        "rank_whey_protein", "rank_whey_protein_isolate", "rank_protein", "rank_sport", "rank_supplements",
        "sold_30d", "rating", "reviews_count",
    ]
    final_cols = [c for c in EXPORT_COLS if c in out_df.columns]
    clean_df = out_df[final_cols].copy()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(OUT_CSV, index=False, sep=';' , encoding='utf-8-sig')
    print(f"Guardado: {OUT_CSV}")

    # ====== MÉTRICAS DE COBERTURA RÁPIDAS (sobre el DF LIMPIO) ======
    cols = [
        "protein_g","calories_kcal","total_fat_g","saturated_fat_g","cholesterol_mg",
        "sodium_mg","total_carbohydrates_g","dietary_fiber_g","total_sugars_g",
        "added_sugars_g","vitamin_d_mcg","calcium_mg","iron_mg","potassium_mg",
        "servings","price_eur","net_weight_g",
        "rank_whey_protein","rank_whey_protein_isolate","rank_protein","rank_sport","rank_supplements",
        "sold_30d","glutamine_g_per_serving", "glutamic_acid_g_per_serving", "rating", "reviews_count",
    ]
    cov = {c: clean_df[c].notna().sum() if c in clean_df.columns else 0 for c in cols}
    cov["total"] = len(clean_df)

    print("\nCobertura (muestra):")
    for k, v in cov.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()


