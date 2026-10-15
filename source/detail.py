# -*- coding: utf-8 -*-
"""
Created on Sat Nov  1 18:15:23 2025

@author: aeget
"""

# source/detail.py
# source/detail.py
import re

def to_float_safe(x: str | None) -> float | None:
    if not x:
        return None
    x = x.strip()
    x = re.sub(r"[^0-9,.\-]+", "", x)
    if "," in x and "." not in x:
        x = x.replace(",", ".")
    try:
        return float(x)
    except:
        return None

def extract_number_with_unit(text: str, unit_regex: str) -> float | None:
    if not text:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(" + unit_regex + r")", text, flags=re.I)
    if not m:
        return None
    return to_float_safe(m.group(1))

def extract_leucine_from_text(text: str) -> float | None:
    if not text:
        return None
    mg = re.search(r"\b(leucine|l[\-\s]?leucine)\b[^0-9]*([\d.,]+)\s*mg", text, flags=re.I)
    g  = re.search(r"\b(leucine|l[\-\s]?leucine)\b[^0-9]*([\d.,]+)\s*g\b",  text, flags=re.I)
    if g:
        return to_float_safe(g.group(2))
    if mg:
        v = to_float_safe(mg.group(2))
        return (v / 1000.0) if v is not None else None
    return None


def _extract_amino_generic(text: str, names: list[str]) -> float | None:
    """
    Busca cantidades por ración de un aminoácido dado (en g o mg).
    Prioriza el bloque 'Amino Acid Profile' si existe; si no, busca globalmente.
    Devuelve valor en gramos (g) o None si no encuentra.
    """
    if not text:
        return None
    t = text

    # 1) Intentar localizar "Amino Acid Profile" y acotar ventana
    block = None
    m = re.search(r"amino\s+acid\s+profile", t, flags=re.I)
    if m:
        block = t[m.start(): m.start() + 4000]
    haystack_list = [b for b in [block] if b] + [t]  # primero profile, luego global

    # 2) Patrones típicos por línea: "Glutamine 4.8 g" / "Glutamic Acid 4600 mg"
    name_pat = "|".join([re.escape(n) for n in names])
    line_rx = re.compile(rf"(?:^|\n)\s*(?:L-)?(?:{name_pat})[^\n]*?([\d.,]+)\s*(mg|g)\b", re.I)

    # 3) Patrones en frase: "... 4.6 g of Glutamic Acid per serving"
    phrase_rx = re.compile(rf"([\d.,]+)\s*(mg|g)\s+of\s+(?:L-)?(?:{name_pat})\s+per\s+serving", re.I)

    for hay in haystack_list:
        # línea tipo tabla
        m1 = line_rx.search(hay)
        if m1:
            val = to_float_safe(m1.group(1))
            unit = m1.group(2).lower()
            if val is not None:
                if unit == "mg":
                    val = val / 1000.0
                return val
        # frase tipo descripción
        m2 = phrase_rx.search(hay)
        if m2:
            val = to_float_safe(m2.group(1))
            unit = m2.group(2).lower()
            if val is not None:
                if unit == "mg":
                    val = val / 1000.0
                return val
    return None


def extract_glutamine_from_text(text: str) -> float | None:
    """
    Devuelve glutamine g/serving si aparece (o None).
    Busca variantes: 'Glutamine', 'L-Glutamine'.
    """
    return _extract_amino_generic(text, ["Glutamine"])

def extract_glutamic_acid_from_text(text: str) -> float | None:
    """
    Devuelve glutamic acid g/serving si aparece (o None).
    Busca variantes: 'Glutamic Acid'.
    """
    return _extract_amino_generic(text, ["Glutamic Acid"])

def guess_net_weight_from_title(title: str) -> float | None:
    if not title:
        return None
    g  = extract_number_with_unit(title, r"g\b")
    if g: return g
    kg = extract_number_with_unit(title, r"kg\b")
    if kg: return kg * 1000.0
    lb = extract_number_with_unit(title, r"lb\b")
    if lb: return lb * 453.592
    oz = extract_number_with_unit(title, r"oz\b")
    if oz: return oz * 28.3495
    return None
