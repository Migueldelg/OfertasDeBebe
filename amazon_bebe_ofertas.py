#!/usr/bin/env python3
"""
Script para obtener ofertas de productos de bebe de Amazon.es
y publicarlas en Telegram
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
import json
import os
import html
import logging
import logging.handlers
import sys
from datetime import datetime, timedelta

# --- Configuracion de Logging ---
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ofertas_bebe.log")

def setup_logging():
    """Configura logging con rotacion diaria y limpieza automatica de logs mayores a 5 dias."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-7s] %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S'
    )

    # Handler de consola: solo si hay terminal interactiva (evita duplicados cuando
    # cron/launchd redirige stdout al mismo fichero de log)
    if sys.stdout.isatty() or os.getenv('CI'):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Handler de archivo con rotacion a medianoche, conserva 5 dias
    file_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILE,
        when='midnight',
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

setup_logging()
log = logging.getLogger(__name__)

# --- Configuracion de Telegram ---
# Bot y canal antiguos (juegos en oferta):
# TELEGRAM_BOT_TOKEN_OLD = '8467408438:AAHaNBPQi-pVop4MXINo5IL4cgy2ewi0OCI'
# TELEGRAM_CHAT_ID_OLD = '-1003803431246'

# Bot y canal nuevos (ofertas bebe):
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- Configuracion de Amazon ---
PARTNER_TAG = "juegosenoferta-21"
BASE_URL = "https://www.amazon.es"

# Archivo para guardar ofertas ya publicadas
POSTED_BEBE_DEALS_FILE = "posted_bebe_deals.json"

# Headers para simular un navegador moderno
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'Cache-Control': 'max-age=0',
}

# Sesion global para mantener cookies
session = requests.Session()

# Categorias que requieren verificacion de titulos similares
# (para evitar publicar el mismo tipo de producto repetidamente)
CATEGORIAS_VERIFICAR_TITULOS = ["Chupetes", "Juguetes"]

# Categorias que solo se publican una vez por semana (no son compra recurrente)
CATEGORIAS_LIMITE_SEMANAL = ["Tronas", "Camaras seguridad", "Chupetes"]

# Marcas prioritarias (se prefieren cuando hay igualdad de descuento)
MARCAS_PRIORITARIAS = ["dodot", "suavinex", "baby sebamed", "mustela", "waterwipes"]

# Categorias de productos de bebe para buscar
CATEGORIAS_BEBE = [
    {"nombre": "Panales", "emoji": "🧷", "url": "/s?k=pañales+bebe&rh=n%3A1703495031"},
    {"nombre": "Toallitas", "emoji": "🧻", "url": "/s?k=toallitas+bebe&rh=n%3A1703495031"},
    {"nombre": "Cremas bebe", "emoji": "🧴", "url": "/s?k=crema+bebe+culete"},
    {"nombre": "Leche en polvo", "emoji": "🥛", "url": "/s?k=leche+en+polvo+bebe"},
    {"nombre": "Chupetes", "emoji": "🍼", "url": "/s?k=chupetes+bebe&rh=n%3A1703495031"},
    {"nombre": "Biberones", "emoji": "🫗", "url": "/s?k=biberones+bebe&rh=n%3A1703495031"},
    {"nombre": "Juguetes", "emoji": "🧸", "url": "/s?k=juguetes+bebe&rh=n%3A1703495031"},
    {"nombre": "Baneras", "emoji": "🛁", "url": "/s?k=bañera+bebe&rh=n%3A1703495031"},
    {"nombre": "Camaras seguridad", "emoji": "📹", "url": "/s?k=camara+vigilancia+bebe"},
    {"nombre": "Alimentacion", "emoji": "🥣", "url": "/s?k=potitos+bebe+papilla"},
    {"nombre": "Tronas", "emoji": "🪑", "url": "/s?k=trona+bebe"},
    {"nombre": "Vajilla bebe", "emoji": "🍽️", "url": "/s?k=platos+cubiertos+vasos+bebe"},
]


def load_posted_deals():
    """
    Carga las ofertas publicadas (ultimas 48h) desde un archivo JSON.
    Retorna tupla: (dict_ofertas, ultimas_categorias, ultimos_titulos)
    - ultimas_categorias: lista de las ultimas 4 categorias publicadas
    - ultimos_titulos: lista de los ultimos 4 titulos publicados (para categorias especificas)
    """
    if not os.path.exists(POSTED_BEBE_DEALS_FILE):
        log.info("No existe historial previo de ofertas publicadas, empezando desde cero")
        return {}, [], [], {}

    with open(POSTED_BEBE_DEALS_FILE, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            log.warning("El archivo de historial esta corrupto, ignorando y empezando desde cero")
            return {}, [], [], {}

    if not isinstance(data, dict):
        log.warning("Formato de historial inesperado, ignorando y empezando desde cero")
        return {}, [], [], {}

    # Extraer ultimas categorias publicadas (lista de hasta 4)
    ultimas_categorias = data.pop('_ultimas_categorias', [])
    # Compatibilidad con formato anterior (string simple)
    if not ultimas_categorias:
        ultima_cat = data.pop('_ultima_categoria', None)
        ultimas_categorias = [ultima_cat] if ultima_cat else []

    # Extraer ultimos titulos publicados (para verificacion de similitud)
    ultimos_titulos = data.pop('_ultimos_titulos', [])

    # Extraer timestamps de ultima publicacion de categorias con limite semanal
    categorias_semanales = data.pop('_categorias_semanales', {})

    recent_deals = {}
    expired_count = 0
    now = datetime.now()
    forty_eight_hours_ago = now - timedelta(hours=48)

    for deal_id, timestamp_str in data.items():
        try:
            post_time = datetime.fromisoformat(timestamp_str)
            if post_time > forty_eight_hours_ago:
                recent_deals[deal_id] = timestamp_str
            else:
                expired_count += 1
        except (ValueError, TypeError):
            continue

    log.info(
        "Historial cargado: %d ASINs en ventana de 48h (ignorados %d expirados)",
        len(recent_deals), expired_count
    )
    if ultimas_categorias:
        log.info("Ultimas categorias publicadas (anti-repeticion): %s", ", ".join(ultimas_categorias))
    if ultimos_titulos:
        log.debug("Ultimos titulos guardados para anti-similitud: %d titulos", len(ultimos_titulos))
    if categorias_semanales:
        for cat, ts in categorias_semanales.items():
            try:
                ultima = datetime.fromisoformat(ts)
                dias = (now - ultima).days
                log.debug("  Categoria '%s' con limite semanal: ultima publicacion hace %d dias (%s)", cat, dias, ultima.strftime('%d/%m %H:%M'))
            except (ValueError, TypeError):
                pass

    return recent_deals, ultimas_categorias, ultimos_titulos, categorias_semanales


def save_posted_deals(deals_dict, ultimas_categorias=None, ultimos_titulos=None, categorias_semanales=None):
    """Guarda el diccionario de ofertas publicadas en un archivo JSON."""
    data = deals_dict.copy()
    if ultimas_categorias:
        data['_ultimas_categorias'] = ultimas_categorias
    if ultimos_titulos:
        data['_ultimos_titulos'] = ultimos_titulos
    if categorias_semanales:
        data['_categorias_semanales'] = categorias_semanales
    with open(POSTED_BEBE_DEALS_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def normalizar_titulo(titulo):
    """Normaliza un titulo para comparacion: minusculas, sin palabras comunes."""
    palabras_ignorar = {
        'de', 'para', 'con', 'sin', 'el', 'la', 'los', 'las', 'un', 'una',
        'unos', 'unas', 'y', 'o', 'a', 'en', 'del', 'al', 'bebe', 'bebé',
        'pack', 'set', 'unidades', 'meses', 'años', 'mese', 'ano',
    }
    titulo_lower = titulo.lower()
    # Extraer solo palabras alfanumericas
    palabras = re.findall(r'\b[a-záéíóúñü]+\b', titulo_lower)
    # Filtrar palabras comunes y muy cortas
    palabras_clave = [p for p in palabras if p not in palabras_ignorar and len(p) > 2]
    return set(palabras_clave)


def titulos_similares(titulo1, titulo2, umbral=0.5):
    """
    Compara dos titulos y determina si son similares.
    Retorna True si comparten mas del umbral (50%) de palabras clave.
    """
    palabras1 = normalizar_titulo(titulo1)
    palabras2 = normalizar_titulo(titulo2)

    if not palabras1 or not palabras2:
        return False

    # Calcular similitud: palabras en comun / total de palabras unicas
    comunes = palabras1 & palabras2
    total = palabras1 | palabras2

    if not total:
        return False

    similitud = len(comunes) / len(total)
    return similitud >= umbral


def titulo_similar_a_recientes(titulo, ultimos_titulos):
    """Verifica si un titulo es similar a alguno de los titulos recientes."""
    for titulo_reciente in ultimos_titulos:
        if titulos_similares(titulo, titulo_reciente):
            return True
    return False


def obtener_prioridad_marca(titulo):
    """
    Extrae la marca del titulo y retorna su prioridad.
    - 1: marca prioritaria encontrada
    - 0: sin marca prioritaria
    Esto se usa como criterio de ordenamiento (mayor prioridad = se ordena primero).
    """
    titulo_lower = titulo.lower()
    for marca in MARCAS_PRIORITARIAS:
        if marca.lower() in titulo_lower:
            return 1
    return 0


def send_telegram_message(message):
    """Envia un mensaje al canal de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        log.info("Mensaje enviado a Telegram correctamente (solo texto)")
        return True
    except requests.exceptions.RequestException as e:
        log.error("Error al enviar mensaje a Telegram: %s", e)
        return False


def send_telegram_photo(photo_url, caption):
    """Envia una foto con caption al canal de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'photo': photo_url,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        log.info("Mensaje enviado a Telegram correctamente (con foto)")
        return True
    except requests.exceptions.RequestException as e:
        log.warning("Error al enviar foto a Telegram (%s), reintentando solo con texto...", e)
        return send_telegram_message(caption)


def format_telegram_message(producto, categoria):
    """Formatea un producto para enviarlo a Telegram."""
    titulo = html.escape(producto['titulo'])
    precio = producto['precio']
    precio_anterior = producto.get('precio_anterior')
    url = producto['url']
    emoji = categoria.get('emoji', '🛍️')
    categoria_nombre = categoria.get('nombre', 'Bebe')

    # Calcular descuento si hay precio anterior
    descuento_texto = ""
    if precio_anterior:
        try:
            precio_num = float(precio.replace('€', '').replace(',', '.').strip())
            precio_ant_num = float(precio_anterior.replace('€', '').replace(',', '.').strip())
            descuento = ((precio_ant_num - precio_num) / precio_ant_num) * 100
            descuento_texto = f" (-{descuento:.0f}%)"
        except:
            descuento_texto = ""

    message = f"{emoji} <b>OFERTA {categoria_nombre.upper()}</b> {emoji}\n\n"
    message += f"📦 <b>{titulo}</b>\n\n"

    if precio_anterior:
        message += f"💰 Precio: <s>{precio_anterior}</s> → <b>{precio}</b>{descuento_texto}\n"
    else:
        message += f"💰 Precio: <b>{precio}</b>\n"

    message += f"\n🛒 <a href='{url}'>Ver en Amazon</a>"

    return message


def obtener_pagina(url, reintentos=3):
    """Obtiene el contenido HTML de una pagina con reintentos."""
    headers = HEADERS.copy()
    headers['Referer'] = 'https://www.amazon.es/'

    for intento in range(reintentos):
        try:
            # Delay aleatorio más largo para parecer humano
            time.sleep(random.uniform(2, 4))
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if intento < reintentos - 1:
                wait_time = random.uniform(5, 10) * (intento + 1)
                log.warning(
                    "Error al obtener pagina (intento %d/%d): %s - Reintentando en %.0fs",
                    intento + 1, reintentos, e, wait_time
                )
                time.sleep(wait_time)
            else:
                log.error("Fallo definitivo al obtener pagina tras %d intentos: %s | URL: %s", reintentos, e, url)
                return None


def extraer_productos_busqueda(html_content):
    """Extrae productos de una pagina de busqueda de Amazon."""
    productos = []
    soup = BeautifulSoup(html_content, 'html.parser')
    items = soup.select('[data-component-type="s-search-result"]')

    for item in items[:20]:  # Mas productos para encontrar ofertas
        try:
            asin = item.get('data-asin', '')
            if not asin:
                continue

            titulo_elem = item.select_one('h2 a span') or item.select_one('h2 span')
            titulo = titulo_elem.get_text(strip=True) if titulo_elem else "Sin titulo"

            precio = "N/A"
            precio_elem = item.select_one('.a-price .a-offscreen')
            if precio_elem:
                precio = precio_elem.get_text(strip=True)

            precio_anterior = None
            precio_anterior_elem = item.select_one('.a-price[data-a-strike="true"] .a-offscreen')
            if precio_anterior_elem:
                precio_anterior = precio_anterior_elem.get_text(strip=True)

            # Calcular descuento
            descuento = 0
            if precio_anterior and precio != "N/A":
                try:
                    precio_num = float(precio.replace('€', '').replace(',', '.').strip())
                    precio_ant_num = float(precio_anterior.replace('€', '').replace(',', '.').strip())
                    if precio_ant_num > 0:
                        descuento = ((precio_ant_num - precio_num) / precio_ant_num) * 100
                except:
                    descuento = 0

            # Extraer numero de valoraciones
            valoraciones = 0
            valoraciones_elem = item.select_one('.a-size-base.s-underline-text') or item.select_one('[aria-label*="estrellas"] + span')
            if valoraciones_elem:
                try:
                    val_text = valoraciones_elem.get_text(strip=True).replace('.', '').replace(',', '')
                    valoraciones = int(re.sub(r'[^\d]', '', val_text) or 0)
                except:
                    valoraciones = 0

            # Extraer ventas (ej: "10K+ comprados el mes pasado")
            ventas = 0
            ventas_elem = item.select_one('.a-size-base.a-color-secondary')
            if ventas_elem:
                ventas_text = ventas_elem.get_text(strip=True).lower()
                if 'compra' in ventas_text or 'vendido' in ventas_text:
                    try:
                        match = re.search(r'(\d+)[kK]?\+?', ventas_text)
                        if match:
                            ventas = int(match.group(1))
                            if 'k' in ventas_text.lower():
                                ventas *= 1000
                    except:
                        ventas = 0

            imagen = ""
            img_elem = item.select_one('img.s-image')
            if img_elem:
                imagen = img_elem.get('src', '')

            url_afiliado = f"{BASE_URL}/dp/{asin}?tag={PARTNER_TAG}"

            productos.append({
                'asin': asin,
                'titulo': titulo[:100] + "..." if len(titulo) > 100 else titulo,
                'precio': precio,
                'precio_anterior': precio_anterior,
                'descuento': descuento,
                'valoraciones': valoraciones,
                'ventas': ventas,
                'imagen': imagen,
                'url': url_afiliado,
                'tiene_oferta': precio_anterior is not None
            })

        except Exception:
            continue

    return productos


def buscar_y_publicar_ofertas():
    """
    Busca la mejor oferta de cada categoria y publica solo la que tenga
    mayor descuento de entre todas.
    """
    log.info("=" * 60)
    log.info("INICIO - BUSCADOR DE OFERTAS DE BEBE | Amazon.es -> Telegram")
    log.info("Tag de afiliado: %s | Hora: %s", PARTNER_TAG, datetime.now().strftime('%d/%m/%Y %H:%M'))
    log.info("=" * 60)

    # Cargar ofertas ya publicadas (ultimas 48h), ultimas categorias y titulos
    posted_deals, ultimas_categorias, ultimos_titulos, categorias_semanales = load_posted_deals()
    posted_asins = set(posted_deals.keys())

    if ultimas_categorias:
        log.info(
            "Anti-repeticion de categoria: se evitaran las ultimas %d categorias [%s]",
            len(ultimas_categorias), ", ".join(ultimas_categorias)
        )
    if ultimos_titulos:
        log.info(
            "Anti-titulo-similar activo para categorias %s (%d titulos recientes guardados)",
            ", ".join(CATEGORIAS_VERIFICAR_TITULOS), len(ultimos_titulos)
        )

    now = datetime.now()
    una_semana = timedelta(days=7)

    # Recopilar la mejor oferta de cada categoria
    mejores_por_categoria = []

    for categoria in CATEGORIAS_BEBE:
        log.info("")
        log.info("--- Categoria: %s ---", categoria['nombre'])

        # Verificar limite semanal para ciertas categorias
        if categoria['nombre'] in CATEGORIAS_LIMITE_SEMANAL:
            ultima_pub_str = categorias_semanales.get(categoria['nombre'])
            if ultima_pub_str:
                try:
                    ultima_pub = datetime.fromisoformat(ultima_pub_str)
                    tiempo_transcurrido = now - ultima_pub
                    if tiempo_transcurrido < una_semana:
                        dias_restantes = (una_semana - tiempo_transcurrido).days + 1
                        log.info(
                            "  SALTADA por limite semanal: ultima publicacion el %s (hace %d dias, faltan ~%d dias)",
                            ultima_pub.strftime('%d/%m %H:%M'), tiempo_transcurrido.days, dias_restantes
                        )
                        continue
                    else:
                        log.debug(
                            "  Limite semanal OK: ultima publicacion hace %d dias (supera los 7 requeridos)",
                            tiempo_transcurrido.days
                        )
                except (ValueError, TypeError):
                    pass

        url = BASE_URL + categoria['url']
        html_content = obtener_pagina(url)

        if not html_content:
            log.warning("  No se pudo obtener la pagina, saltando categoria")
            continue

        productos = extraer_productos_busqueda(html_content)
        ofertas = [p for p in productos if p['tiene_oferta']]
        sin_oferta = len(productos) - len(ofertas)
        log.info(
            "  Scraped: %d productos (%d con oferta, %d sin descuento)",
            len(productos), len(ofertas), sin_oferta
        )

        if not ofertas:
            log.info("  No hay productos con descuento en esta categoria")
            continue

        # Ordenar ofertas: primero por mayor descuento, luego marca prioritaria, luego valoraciones, luego ventas
        ofertas_ordenadas = sorted(
            ofertas,
            key=lambda x: (x['descuento'], obtener_prioridad_marca(x['titulo']), x['valoraciones'], x['ventas']),
            reverse=True
        )

        # Log de los top candidatos antes de filtrar
        log.debug("  Top candidatos antes de filtros anti-duplicacion:")
        for i, p in enumerate(ofertas_ordenadas[:5], 1):
            marca_flag = " [MARCA PRIO]" if obtener_prioridad_marca(p['titulo']) else ""
            log.debug(
                "    %d. [%s] %s | %.0f%% dto | %d vals | %d ventas%s",
                i, p['asin'], p['titulo'][:50], p['descuento'],
                p['valoraciones'], p['ventas'], marca_flag
            )

        # Buscar la mejor oferta no publicada en esta categoria
        verificar_titulos = categoria['nombre'] in CATEGORIAS_VERIFICAR_TITULOS
        candidato_elegido = None

        for producto in ofertas_ordenadas:
            asin = producto['asin']
            titulo_corto = producto['titulo'][:45]

            if asin in posted_asins:
                log.info(
                    "  DESCARTADO [ya publicado en <48h] %s... (%.0f%% dto, ASIN: %s)",
                    titulo_corto, producto['descuento'], asin
                )
                continue

            if verificar_titulos and titulo_similar_a_recientes(producto['titulo'], ultimos_titulos):
                log.info(
                    "  DESCARTADO [titulo similar a reciente] %s... (%.0f%% dto)",
                    titulo_corto, producto['descuento']
                )
                continue

            candidato_elegido = producto
            marca_flag = " [marca prioritaria]" if obtener_prioridad_marca(producto['titulo']) else ""
            log.info(
                "  ELEGIDO para categoria: %s... (%.0f%% dto, %d valoraciones, ASIN: %s)%s",
                titulo_corto, producto['descuento'], producto['valoraciones'], asin, marca_flag
            )
            mejores_por_categoria.append({
                'producto': producto,
                'categoria': categoria
            })
            break

        if candidato_elegido is None:
            log.info("  Sin candidatos validos: todos descartados por duplicacion o similitud de titulo")

    # De entre las mejores ofertas de cada categoria, seleccionar la de mayor descuento
    if not mejores_por_categoria:
        log.info("")
        log.info("=" * 60)
        log.info("RESULTADO: No hay ofertas nuevas para publicar en este ciclo")
        log.info("=" * 60)
        return 0

    # Ordenar por descuento y marca prioritaria, seleccionar la mejor
    mejores_por_categoria.sort(
        key=lambda x: (x['producto']['descuento'], obtener_prioridad_marca(x['producto']['titulo'])),
        reverse=True
    )

    log.info("")
    log.info("--- Seleccion global (ranking de mejores por categoria) ---")
    for i, entrada in enumerate(mejores_por_categoria, 1):
        p = entrada['producto']
        cat = entrada['categoria']['nombre']
        marca_flag = " [marca prio]" if obtener_prioridad_marca(p['titulo']) else ""
        en_ultimas = " [cat. reciente]" if cat in ultimas_categorias else ""
        log.info(
            "  %d. [%s] %s... | %.0f%% dto | cat: %s%s%s",
            i, p['asin'], p['titulo'][:40], p['descuento'], cat, marca_flag, en_ultimas
        )

    # Evitar repetir categorias de las ultimas 4 publicaciones, excepto algunas
    mejor_oferta = None
    categorias_excluidas_repeticion = ["Panales", "Toallitas"]

    for oferta in mejores_por_categoria:
        nombre_categoria = oferta['categoria']['nombre']
        if nombre_categoria not in ultimas_categorias or nombre_categoria in categorias_excluidas_repeticion:
            mejor_oferta = oferta
            break

    if mejor_oferta is None:
        log.info(
            "Todas las categorias candidatas estan en el historial reciente [%s], "
            "publicando la mejor disponible igualmente",
            ", ".join(ultimas_categorias)
        )
        mejor_oferta = mejores_por_categoria[0]
    elif mejor_oferta != mejores_por_categoria[0]:
        primera_cat = mejores_por_categoria[0]['categoria']['nombre']
        log.info(
            "Anti-repeticion: la #1 global (%s) fue descartada porque su categoria '%s' "
            "aparece en las recientes [%s]. Se elige la siguiente valida.",
            mejores_por_categoria[0]['producto']['titulo'][:35],
            primera_cat,
            ", ".join(ultimas_categorias)
        )

    producto = mejor_oferta['producto']
    categoria = mejor_oferta['categoria']

    log.info("")
    log.info(">>> OFERTA SELECCIONADA PARA PUBLICAR:")
    log.info("    Titulo:    %s", producto['titulo'])
    log.info("    Categoria: %s | Descuento: %.0f%%", categoria['nombre'], producto['descuento'])
    log.info("    Precio:    %s (antes: %s)", producto['precio'], producto.get('precio_anterior', 'N/A'))
    log.info("    ASIN:      %s | Valoraciones: %d | Ventas: %d",
             producto['asin'], producto['valoraciones'], producto['ventas'])
    log.info("    URL:       %s", producto['url'])

    # Formatear mensaje
    mensaje = format_telegram_message(producto, categoria)

    # Enviar a Telegram (con foto si disponible)
    if producto['imagen']:
        log.debug("    Enviando con foto: %s", producto['imagen'])
        exito = send_telegram_photo(producto['imagen'], mensaje)
    else:
        log.debug("    Enviando sin foto (no disponible)")
        exito = send_telegram_message(mensaje)

    ofertas_publicadas = 0
    if exito:
        posted_deals[producto['asin']] = datetime.now().isoformat()
        # Añadir categoria al inicio de la lista y mantener solo las ultimas 4
        ultimas_categorias.insert(0, categoria['nombre'])
        ultimas_categorias = ultimas_categorias[:4]
        log.debug("Historial de categorias actualizado: %s", ", ".join(ultimas_categorias))

        # Si es categoria con verificacion de titulos, guardar el titulo
        if categoria['nombre'] in CATEGORIAS_VERIFICAR_TITULOS:
            ultimos_titulos.insert(0, producto['titulo'])
            ultimos_titulos = ultimos_titulos[:4]
            log.debug("Titulo guardado en anti-similitud (total: %d)", len(ultimos_titulos))

        # Si es categoria con limite semanal, guardar el timestamp
        if categoria['nombre'] in CATEGORIAS_LIMITE_SEMANAL:
            categorias_semanales[categoria['nombre']] = datetime.now().isoformat()
            log.debug("Timestamp de limite semanal actualizado para categoria '%s'", categoria['nombre'])

        ofertas_publicadas = 1
    else:
        log.error("Fallo al enviar a Telegram, no se guarda el ASIN en el historial")

    # Guardar ofertas publicadas, ultimas categorias y titulos
    save_posted_deals(posted_deals, ultimas_categorias, ultimos_titulos, categorias_semanales)

    log.info("")
    log.info("=" * 60)
    log.info("FIN - %s oferta publicada en Telegram", ofertas_publicadas)
    log.info("=" * 60)

    return ofertas_publicadas


def main(modo_continuo=False):
    """
    Funcion principal.
    - modo_continuo=False: ejecuta una vez y termina (para cron)
    - modo_continuo=True: ejecuta cada 15 minutos en bucle infinito
    """
    if modo_continuo:
        log.info("Modo continuo activado - Ejecutando cada 15 minutos (Ctrl+C para detener)")
        while True:
            try:
                buscar_y_publicar_ofertas()
                log.info("Proxima ejecucion en 15 minutos...")
                log.info("-" * 60)
                time.sleep(900)  # 15 minutos = 900 segundos
            except KeyboardInterrupt:
                log.info("Detenido por el usuario (Ctrl+C)")
                break
    else:
        # Ejecutar una sola vez (ideal para cron)
        buscar_y_publicar_ofertas()


if __name__ == "__main__":
    import sys

    # Si se pasa --continuo, ejecuta en bucle cada 15 minutos
    modo_continuo = "--continuo" in sys.argv or "-c" in sys.argv
    main(modo_continuo=modo_continuo)
