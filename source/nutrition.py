# -*- coding: utf-8 -*-
"""
Created on Sat Nov  1 18:40:59 2025

@author: aeget
"""

# source/nutrition.py
import re
from .detail import to_float_safe

# Posibles encabezados de la tabla
ANCHORS = [
    r"nutrition\s+information",
    r"nutrition\s+facts",
    r"nutritional\s+information",
    r"supplement\s+facts",
    r"supplement\s+information",
]

# Regex de nutrientes clave (solo “Amount per serving”)
NUTRIENT_MAP = [
    (r"^calories$",                         "calories_kcal",          "kcal"),
    (r"^total\s+fat$",                       "total_fat_g",            "g"),
    (r"^saturated\s+fat$",                   "saturated_fat_g",        "g"),
    (r"^trans\s+fat$",                       "trans_fat_g",            "g"),
    (r"^cholesterol$",                       "cholesterol_mg",         "mg"),
    (r"^sodium$",                            "sodium_mg",              "mg"),
    (r"^total\s+carbohydrates?$",            "total_carbohydrates_g",  "g"),
    (r"^dietary\s+fibre$|^dietary\s+fiber$", "dietary_fiber_g",        "g"),
    (r"^total\s+sugars?$",                   "total_sugars_g",         "g"),
    (r"^includes\s+.*added\s+sugars?$",      "added_sugars_g",         "g"),
    (r"^protein$",                           "protein_g",              "g"),
    (r"^vitamin\s+d$",                       "vitamin_d_mcg",          "mcg"),
    (r"^calcium$",                           "calcium_mg",             "mg"),
    (r"^iron$",                              "iron_mg",                "mg"),
    (r"^potassium$",                         "potassium_mg",           "mg"),
]

def _slice_block_after_anchor(text: str, window_chars: int = 6000) -> str | None:
    """Recorta un bloque de texto a partir del encabezado “Nutrition …”."""
    if not text:
        return None
    low = text.lower()
    for pat in ANCHORS:
        m = re.search(pat, low, flags=re.I)
        if m:
            return text[m.start(): m.start() + window_chars]
    return None

def _first_number_g(s: str) -> float | None:
    """Devuelve el primer número en gramos si existe."""
    if not s:
        return None
    m = re.search(r"([\d.,]+)\s*g\b", s, flags=re.I)
    return to_float_safe(m.group(1)) if m else None

def _parse_amount_and_unit(s: str):
    """Extrae valor y unidad (g/mg/mcg/kcal)."""
    if not s:
        return None, None
    s = s.strip()
    s = re.sub(r"\b\d+\s*%.*$", "", s)
    m = re.search(r"([\d.,]+)\s*(mcg|mg|g|kcal)?\b", s, flags=re.I)
    if not m:
        return None, None
    val = to_float_safe(m.group(1))
    unit = (m.group(2) or "").lower() if m.group(2) else None
    return val, unit

def _normalize_name(name: str) -> str:
    """Normaliza espacios y minúsculas."""
    name = re.sub(r"\s+", " ", name.strip().lower())
    return name

def extract_all_nutrients(visible_text: str) -> dict:
    """
    Extrae:
      - serving_size_text
      - serving_size_g
      - servings (aproximado)
      - todos los nutrientes por serving
    """
    block = _slice_block_after_anchor(visible_text)
    if not block:
        return {}

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    out = {}

    # --- Serving size ---
    for ln in lines:
        m = re.match(r"(?i)serving\s*size\s*[:\-]?\s*(.+)", ln)
        if m:
            txt = m.group(1).strip()
            out["serving_size_text"] = txt
            out["serving_size_g"] = _first_number_g(txt)
            break

    # --- Servings per container ---
    for ln in lines:
        m = re.match(r"(?i)servings?\s+per\s+container\s*[:\-]?\s*([\w\s.,]+)", ln)
        if m:
            out["servings_text"] = m.group(1).strip()
            # si hay número, extraer
            mnum = re.search(r"([\d.,]+)", out["servings_text"])
            if mnum:
                out["servings"] = to_float_safe(mnum.group(1))
            break

    # --- Nutrientes ---
    for ln in lines:
        # Busca patrón “Nombre + cantidad + unidad”
        m = re.search(r"(.*?)([\d.,]+\s*(?:mcg|mg|g|kcal))\b", ln, flags=re.I)
        if not m:
            continue
        left = _normalize_name(m.group(1))
        right = m.group(2).strip()

        for pat, dest_key, expected_unit in NUTRIENT_MAP:
            if re.match(pat, left, flags=re.I):
                val, unit = _parse_amount_and_unit(right)
                if val is None:
                    break
                if expected_unit == "kcal" and not unit:
                    unit = "kcal"
                # conversión mínima
                if unit == "mcg" and expected_unit == "mg":
                    val /= 1000.0
                elif unit == "mg" and expected_unit == "mcg":
                    val *= 1000.0
                out[dest_key] = val
                break

    return out
