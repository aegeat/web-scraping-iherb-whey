# -*- coding: utf-8 -*-
"""
Created on Sun Oct 26 16:41:51 2025

@author: aeget
"""

# source/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- Información general del proyecto ---
PROJECT_NAME = "Práctica 1 Tipología"
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "aegeat@uoc.edu")

# --- User-Agent realista ---
# Simula un navegador moderno de macOS con Chrome.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.0.0 Safari/537.36"
)

# --- Cabeceras HTTP completas ---
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.8",
    "Cache-Control": "no-cache",
    "DNT": "1",  # Do Not Track
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": USER_AGENT,
}

# --- URL inicial (semilla) ---
SEED_URL = "https://www.iherb.com/c/protein"

# --- Parámetros de red ---
REQUEST_TIMEOUT = 20  # segundos
SLEEP_MIN = 1.5
SLEEP_MAX = 3.5

# --- Logs ---
LOG_LEVEL = "INFO"
LOG_FILE = None  # o "logs/step1.log" si quieres registrar en archivo

ROBOTS_STRICT = False  # dejamos False para avanzar con diagnóstico

# Prefijos whitelisted en iHerb (categorías /c/ y productos /pr/):
ROBOTS_LENIENT_WHITELIST_PREFIXES = [
    "https://www.iherb.com/c/",
    "https://iherb.com/c/",
    "https://www.iherb.com/pr/",
    "https://iherb.com/pr/",
]