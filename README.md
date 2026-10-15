# Proyecto: Web Scraping de Proteínas – iHerb

Este proyecto forma parte de una práctica universitaria sobre **tipología y ciclo de vida de los datos**, cuyo objetivo es realizar un proceso completo de **extracción, transformación y carga (ETL)** a partir de datos obtenidos de la web.

El proyecto recopila información detallada sobre productos de **proteína en polvo** disponibles en la tienda en línea [iHerb](https://www.iherb.com/), utilizando Python y técnicas de web scraping.

---

## Estructura del proyecto

```
pra1/
│
├── source/
│   ├── browser.py              # Configura Selenium y el WebDriver
│   ├── config.py               # Parámetros generales (SEED_URL, User-Agent, etc.)
│   ├── listing.py              # Funciones para extraer las tarjetas de producto
│   ├── detail.py               # Extracción de aminoácidos, ingredientes, ratings y rankings
│   ├── nutrition.py            # Parsing de la información nutricional
│   ├── step1_list_all.py       # Recolecta todas las URLs de la categoría de proteínas
│   ├── step2_main.py           # Extrae todos los detalles nutricionales y los guarda en CSV
│
│
├── dataset/
│   ├── protein_listing_urls.csv   # URLs de producto (salida del paso 1)
│   ├── protein_details_partial_with_reviews.csv        # Datos parciales con reviews (salida del paso 2) antes del bloqueo por captcha
│   ├── protein_details_complete_without_reviews.csv    # Datos completos sin reviews (salida del paso 2) antes del bloqueo por captcha
│
├── requirements.txt
└── README.md
```

---

## Instalación

1. Clonar o copiar este repositorio.
2. Instalar las dependencias necesarias:

```bash
pip install -r requirements.txt
```

3. Verificar que **Google Chrome** esté instalado.
   El proyecto utiliza `webdriver-manager` para descargar automáticamente la versión correcta de `chromedriver`.

---

## Ejecución

### Paso 1 – Listar productos

Crea un listado completo de todas las URLs de la categoría `protein` de iHerb:

```bash
python source/step1_list_all.py
```

Esto genera el archivo:

```
dataset/protein_listing_urls.csv
```

---

### Paso 2 – Extraer detalles

Raspa los datos completos (nutrición, ingredientes, aminoácidos, valoraciones, rankings, etc.) de cada producto listado:

```bash
python source/step2_main.py
```

Esto genera el archivo:

```
dataset/protein_details.csv
```

---

## Datos extraídos

Cada registro (fila) del CSV resultante representa un producto e incluye las siguientes columnas principales:

| Tipo de dato                | Campos extraídos                                                                                                                                                            |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Identificación**          | `title`, `url`                                                                                                                                                              |
| **Precio y tamaño**         | `price_eur`, `net_weight_g`, `selected_size_g`                                                                                                                              |
| **Información nutricional** | `serving_size_text`, `serving_size_g`, `servings`, `calories_kcal`, `protein_g`, `total_fat_g`, `carbohydrates_g`, `vitamin_d_mcg`, `calcium_mg`, `iron_mg`, `potassium_mg` |
| **Aminoácidos**             | `leucine_g_per_serving`, `glutamine_g_per_serving`, `glutamic_acid_g_per_serving`                                                                                           |
| **Ingredientes**            | `ingredients_text`                                                                                                                                                          |
| **Popularidad y posición**  | `rank_whey_protein`, `rank_protein`, `rank_sport`, `rank_supplements`, `sold_30d`                                                                                           |
| **Valoraciones**            | `rating`, `reviews_count`                                                                                                                                                   |

---

## Consideraciones éticas y legales

* Este proyecto se ha desarrollado con fines **exclusivamente educativos** dentro del Máster Universitario en Ciencia de Datos (UOC).
* Se han respetado las directrices del archivo `robots.txt` de iHerb, evitando el acceso a rutas restringidas.
* Los datos recopilados proceden únicamente de **información pública visible** en la web.
* No se ha realizado ningún uso comercial ni automatización masiva que pudiera afectar al servicio original.

---

## Aspectos técnicos destacados

* **Selenium WebDriver** con `webdriver-manager` permite simular la navegación real y acceder a contenido dinámico generado por JavaScript.
* **Expresiones regulares** flexibles extraen nutrientes, aminoácidos y precios incluso cuando el formato HTML varía entre productos.
* Se incorporan funciones de **espera explícita y scroll progresivo**, además de cierres automáticos de pop-ups, para asegurar la correcta carga del contenido.
* El dataset final se exporta con separador `;` y codificación `utf-8-sig`.
---
