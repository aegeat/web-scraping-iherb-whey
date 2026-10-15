# -*- coding: utf-8 -*-
"""
Created on Sun Oct 26 16:55:51 2025

@author: aeget
"""

# source/browser.py
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SLEEP_MIN = 1.5
SLEEP_MAX = 3.5

def polite_sleep():
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

def get_driver(headless=False, user_agent=None, lang="en-US,en;q=0.9"):
    chrome_options = Options()

    # Headless opcional
    if headless:
        # El modo "new" va mejor con Selenium Manager
        chrome_options.add_argument("--headless=new")

    # User-Agent realista
    if user_agent:
        chrome_options.add_argument(f"--user-agent={user_agent}")
    else:
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )

    # Pequeños ajustes anti-detección y estabilidad
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f"--lang={lang}")
    chrome_options.add_argument("--window-size=1200,900")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Clave: no pasamos ejecutable ni Service -> Selenium Manager se encarga
    driver = webdriver.Chrome(options=chrome_options)

    polite_sleep()
    return driver
