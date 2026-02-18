# AGENTS.md - Referencia Técnica para Agentes IA

## Contexto Rápido

Bot de scraping que:
1. Busca ofertas en Amazon.es por categorías de bebé
2. Selecciona la mejor oferta global (mayor descuento)
3. La publica en un canal de Telegram
4. Evita duplicados mediante un JSON de tracking

**Estructura de archivos:**
- `shared/amazon_ofertas_core.py` — funciones genéricas compartidas (scraping, Telegram, utilidades)
- `bebe/amazon_bebe_ofertas.py` — configuración de bebé + wrappers + lógica principal
- `bebe/posted_bebe_deals.json` — estado anti-duplicados del canal bebé
- `bebe/tests/` — 64 tests automatizados

---

## Constantes de Configuración Clave

Todas en `bebe/amazon_bebe_ofertas.py`:

| Constante | Línea | Descripción |
|-----------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | ~35 | Token del bot de producción (env var) |
| `TELEGRAM_CHAT_ID` | ~36 | Chat ID del canal de producción (env var) |
| `DEV_TELEGRAM_BOT_TOKEN` | ~39 | Token del bot de desarrollo (env var, mismo que proyecto relases) |
| `DEV_TELEGRAM_CHAT_ID` | ~40 | Chat ID del canal de pruebas (env var, mismo que proyecto relases) |
| `DEV_MODE` | ~43 | Flag booleano; `True` cuando se ejecuta con `--dev` |
| `CATEGORIAS_BEBE` | ~67 | Lista de categorías a buscar |
| `CATEGORIAS_VERIFICAR_TITULOS` | ~58 | Categorías donde se comparan títulos para evitar similares |
| `CATEGORIAS_LIMITE_SEMANAL` | ~61 | Categorías que solo se publican una vez por semana (Tronas, Cámaras seguridad, Chupetes, Vajilla bebe) |
| `MARCAS_PRIORITARIAS` | ~64 | Marcas preferidas cuando hay igualdad de descuento |

---

## Tareas Comunes

### Añadir nueva categoría

Editar `CATEGORIAS_BEBE` (línea ~52 en `bebe/amazon_bebe_ofertas.py`):
```python
{"nombre": "NombreVisible", "emoji": "🆕", "url": "/s?k=busqueda+amazon"}
```

### Activar verificación de títulos en una categoría

Editar `CATEGORIAS_VERIFICAR_TITULOS` (línea ~43):
```python
CATEGORIAS_VERIFICAR_TITULOS = ["Chupetes", "Juguetes", "NuevaCategoria"]
```

### Activar límite semanal en una categoría

Editar `CATEGORIAS_LIMITE_SEMANAL` (línea ~46):
```python
CATEGORIAS_LIMITE_SEMANAL = ["Tronas", "Camaras seguridad", "Chupetes", "Vajilla bebe"]
```

> Los nombres deben coincidir exactamente con el campo `nombre` en `CATEGORIAS_BEBE`.

### Añadir o modificar marcas prioritarias

Editar `MARCAS_PRIORITARIAS` (línea ~49):
```python
MARCAS_PRIORITARIAS = ["dodot", "suavinex", "baby sebamed", "mustela", "waterwipes"]
```

Estas marcas se priorizan cuando hay **igualdad de descuento**. La búsqueda es case-insensitive y busca si el nombre de la marca aparece en el título del producto.

### Cambiar frecuencia en modo continuo

`time.sleep(900)` en `main()` — valor en segundos.

### Cambiar ventana anti-duplicados de ASINs

`timedelta(hours=48)` en `load_posted_deals()` del core.

### Modificar formato del mensaje de Telegram

Función `format_telegram_message()` en `amazon_ofertas_core.py`.

### Cambiar criterio de ordenación de ofertas

En `buscar_y_publicar_ofertas()` (línea ~99 en `amazon_bebe_ofertas.py`):
```python
key=lambda x: (x['descuento'], obtener_prioridad_marca(x['titulo']), x['valoraciones'], x['ventas'])
```

El criterio actual ordena por:
1. **Descuento** (mayor primero)
2. **Marca prioritaria** (1 si es marca en `MARCAS_PRIORITARIAS`, 0 si no)
3. **Valoraciones** (mayor primero)
4. **Ventas** (mayor primero)

Esto asegura que con igual descuento, se prefieren las marcas definidas en `MARCAS_PRIORITARIAS`.

### Ajustar umbral de similitud de títulos

Parámetro `umbral` en `titulos_similares()` del core (por defecto `0.5` = 50%).

---

## Estructura de Datos

### Producto (extraído de Amazon)
```python
{
    'asin': str,            # ID único de Amazon
    'titulo': str,          # Max 100 chars
    'precio': str,          # "12,99€"
    'precio_anterior': str, # "19,99€" o None
    'descuento': float,     # Porcentaje calculado
    'valoraciones': int,    # Número de reviews
    'ventas': int,          # Ventas del mes
    'imagen': str,          # URL de imagen
    'url': str,             # URL con tag afiliado
    'tiene_oferta': bool    # True si hay precio_anterior
}
```

### Categoría
```python
{
    'nombre': str,  # Nombre visible (debe coincidir exactamente con las listas de control)
    'emoji': str,   # Emoji para el mensaje de Telegram
    'url': str      # URL relativa de búsqueda en Amazon
}
```

### Archivo JSON (`bebe/posted_bebe_deals.json`)
```json
{
    "_ultimas_categorias": ["Juguetes", "Panales", "Chupetes", "Tronas"],
    "_ultimos_titulos": ["Philips Avent Chupete ultra soft...", "Fisher-Price..."],
    "_categorias_semanales": {
        "Tronas": "2024-01-15T10:30:00",
        "Camaras seguridad": "2024-01-10T08:00:00",
        "Vajilla bebe": "2024-01-12T09:00:00"
    },
    "B08XYZ123": "2024-01-15T10:30:00",
    "B07ABC456": "2024-01-14T18:45:00"
}
```

- `_ultimas_categorias`: hasta 4 categorías recientes (más reciente primero), para evitar repetición
- `_ultimos_titulos`: hasta 4 títulos de categorías con verificación, para evitar similares
- `_categorias_semanales`: timestamp de última publicación por categoría con límite semanal
- Resto de claves: `ASIN → timestamp ISO` (ventana de 48h anti-duplicados)

---

## Lógica de Selección de Ofertas

```
1. Cargar estado desde JSON

2. Para cada categoría en CATEGORIAS_BEBE:
   ├─ ¿Tiene límite semanal y fue publicada hace <7 días? → Saltar categoría
   ├─ Obtener página de Amazon
   └─ Para cada oferta (ordenada por descuento desc):
      ├─ ¿ASIN ya publicado en últimas 48h? → Siguiente oferta
      ├─ ¿Categoría en VERIFICAR_TITULOS y título similar a recientes? → Siguiente oferta
      └─ ✓ Guardar como mejor de esta categoría y pasar a siguiente categoría

3. **Agrupar variantes** del mismo producto:
   ├─ Detectar si dos productos son variantes (ej: FIFA 26 PS4 ↔ FIFA 26 PS5)
   ├─ Representante: el de mayor descuento (desempate: valoraciones)
   └─ Variantes adicionales: guardadas en campo `variantes_adicionales`

4. De todas las mejores por categoría (ordenadas por descuento):
   └─ Para cada una:
      ├─ ¿Categoría en las últimas 4 publicadas? → Siguiente (si hay más opciones)
      └─ ✓ Seleccionar para publicar

5. Si todas son de categorías recientes → publicar la de mayor descuento igualmente

6. Publicar en Telegram con formato especial si hay variantes:
   - Múltiples links clicables (uno por cada variante)
   - Identificadores auto-extraídos (PS4, AZUL, etc.)
   - Guardar ASINs de todas las variantes en posted_deals para evitar re-publicar

7. Guardar estado actualizado
```

---

## Sistema de Agrupamiento de Variantes

Cuando dos productos son **variantes del mismo producto base**, el sistema los agrupa en una sola publicación con múltiples links.

### Detección de Variantes

Dos productos son variantes si:
1. Sus palabras normalizadas tienen **intersección no vacía** (comparten base común)
2. Sus **diferencias** consisten solo en `PALABRAS_VARIANTE` (colores, plataformas, etc.)

```python
# Ejemplos de variantes detectadas:
son_variantes("FIFA 26 PS5", "FIFA 26 PS4")        → True ✓
son_variantes("Chicco Rosa", "Chicco Azul")        → True ✓
son_variantes("FIFA 26 PS5", "Mando DualSense")    → False ✗
```

**Insight clave:** PS5/PS4 son "invisibles" en normalización porque `normalizar_titulo()` extrae solo letras (regex `\b[a-záéíóúñü]+\b`), así que "PS5" → "ps" → descartado (≤2 letras). Esto hace que "FIFA 26 PS4" y "FIFA 26 PS5" normalicen ambos a `{fifa}`, permitiendo detección automática sin reglas especiales.

### Conjunto de Palabras Variante

```python
PALABRAS_VARIANTE = {
    # Colores
    'rojo', 'roja', 'azul', 'verde', 'rosa', 'negro', 'negra',
    'blanco', 'blanca', 'amarillo', 'amarilla', 'naranja',
    'morado', 'morada', 'violeta', 'gris', 'beige', 'marron',
    'dorado', 'dorada', 'plateado', 'plateada', 'lila', 'turquesa',
    # Tamaños/Variantes
    'mini', 'maxi',
}
```

### Formato Telegram con Variantes

**Con variantes:**
```
🎮 OFERTA JUEGOS PS5 🎮

📦 FIFA 26 PS5

💰 39,99€ <s>69,99€</s> (-43%)
💰 34,99€ <s>58,99€</s> (-40%) (PS4)
```

**Sin variantes (preserva formato original):**
```
🎮 OFERTA JUEGOS PS5 🎮

📦 Mando DualSense

💰 Precio: 74,99€ → 59,99€ (-20%)

🛒 Ver en Amazon
```

### Extracción Automática de Identificadores

El código extrae automáticamente qué diferencia a cada variante:

1. **Patrón 1:** Busca `PS#`, `Gen#`, etc. (letras+números: `[a-z]{1,3}\d+`)
2. **Patrón 2:** Si no encuentra, extrae palabras normalizadas diferentes
3. **Mostrada:** Aparece en paréntesis `(PS4)`, `(AZUL)` junto al precio

```python
# Ejemplos:
"FIFA 26 PS4" → extrae "PS4" ✓
"Chicco Azul" → extrae "AZUL" ✓
"Mando Gen2" → extrae "GEN2" ✓
```

### Guardado de Variantes en Anti-Duplicados

Cuando se publica un grupo con variantes:
```python
posted_deals[producto_principal['asin']] = datetime.now().isoformat()
# Guardar también ASINs de variantes para evitar re-publicar
for variante in producto_principal.get('variantes_adicionales', []):
    posted_deals[variante['asin']] = datetime.now().isoformat()
```

Esto previene que cualquier variante se publique nuevamente en los próximos 48h.

---

## Funciones Importantes

### `bebe/amazon_bebe_ofertas.py` (wrappers de dominio)

| Función | Descripción | Línea |
|---------|-------------|-------|
| `_effective_token()` | Devuelve el token dev si `DEV_MODE`, si no el de prod | ~49 |
| `_effective_chat_id()` | Devuelve el chat_id dev si `DEV_MODE`, si no el de prod | ~53 |
| `obtener_prioridad_marca(titulo)` | Wrapper: llama al core con `MARCAS_PRIORITARIAS` de bebé | ~87 |
| `send_telegram_message(message)` | Wrapper: llama al core con credenciales efectivas (prod o dev) | ~91 |
| `send_telegram_photo(photo_url, caption)` | Wrapper: llama al core con credenciales efectivas (prod o dev) | ~96 |
| `load_posted_deals()` | Wrapper: llama al core con `POSTED_BEBE_DEALS_FILE` | ~101 |
| `save_posted_deals(deals_dict, ...)` | Wrapper: llama al core con `POSTED_BEBE_DEALS_FILE` | ~109 |
| `buscar_y_publicar_ofertas()` | Lógica principal de selección y publicación | ~114 |

### `shared/amazon_ofertas_core.py` (funciones genéricas)

| Función | Descripción | Línea |
|---------|-------------|-------|
| `normalizar_titulo(titulo)` | Extrae palabras clave del título (normaliza a set) | ~130 |
| `son_variantes(titulo1, titulo2)` | Detecta si dos productos son variantes del mismo producto | ~211 |
| `agrupar_variantes(mejores_por_categoria)` | Agrupa variantes usando Union-Find; retorna lista con `variantes_adicionales` | ~235 |
| `format_telegram_message(producto, categoria)` | Formatea mensaje Telegram con soporte para variantes | ~380 |
| `obtener_prioridad_marca(titulo, marcas)` | Detecta si un título contiene una marca de la lista; retorna 1 o 0 | ~179 |
| `titulo_similar_a_recientes(titulo, lista)` | Verifica similitud con últimos 4 títulos | ~173 |
| `titulos_similares(t1, t2, umbral)` | Compara dos títulos con umbral configurable (default 50%) | ~157 |
| `normalizar_titulo(titulo)` | Extrae palabras clave de un título para comparación | ~141 |
| `send_telegram_message(message, token, chat_id)` | Envía mensaje de texto a Telegram | ~192 |
| `send_telegram_photo(photo_url, caption, token, chat_id)` | Envía foto a Telegram; fallback a texto | ~209 |
| `format_telegram_message(producto, categoria)` | Formatea el mensaje HTML para Telegram | ~224 |
| `obtener_pagina(url)` | HTTP GET con reintentos y delays anti-bot | ~247 |
| `extraer_productos_busqueda(html)` | Parsea HTML de búsqueda de Amazon | ~267 |
| `load_posted_deals(filepath)` | Carga historial desde JSON, filtra expirados (>48h) | ~80 |
| `save_posted_deals(deals_dict, filepath, ...)` | Persiste historial en JSON | ~130 |

---

## Selectores CSS (Amazon)

Si Amazon cambia su HTML, estos son los selectores a revisar en `extraer_productos_busqueda()` de `shared/amazon_ofertas_core.py`:

| Elemento | Selector |
|----------|----------|
| Contenedor producto | `[data-component-type="s-search-result"]` |
| Título | `h2 a span` |
| Precio actual | `.a-price .a-offscreen` |
| Precio anterior (tachado) | `.a-price[data-a-strike="true"] .a-offscreen` |
| Imagen | `img.s-image` |
| Valoraciones | `.a-size-base.s-underline-text` |
| Ventas | `.a-size-base.a-color-secondary` |

> **Importante:** el orden de los spans de precio en el HTML importa. Amazon pone primero el precio actual (sin `data-a-strike`) y después el tachado (con `data-a-strike="true"`). El selector `.a-price .a-offscreen` coge el primero por eso.

---

## Precauciones

1. **Nombres de categoría:** deben coincidir exactamente entre `CATEGORIAS_BEBE`, `CATEGORIAS_VERIFICAR_TITULOS` y `CATEGORIAS_LIMITE_SEMANAL`
2. **Anti-bot:** no eliminar los delays entre requests (`time.sleep` en `obtener_pagina()`)
3. **Selectores:** Amazon cambia su HTML frecuentemente; si el scraper falla, revisar los selectores
4. **Credenciales:** no hardcodear tokens en el código; usar variables de entorno
5. **Rate limits:** Telegram limita mensajes por segundo; no modificar el flujo para publicar varios a la vez

---

## Testing

```bash
# Ejecutar los 64 tests
python3 -m pytest -v

# Con cobertura
python3 -m pytest --cov=bebe.amazon_bebe_ofertas --cov-report=term-missing

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
```

Los tests cubren: funciones puras, I/O con mocks, parsing HTML y lógica de selección completa.

## Modo Desarrollo (--dev)

Ejecutar con `--dev` publica en el canal de pruebas compartido y **no modifica `posted_bebe_deals.json`**:

| Comportamiento | Producción | Dev (`--dev`) |
|----------------|------------|---------------|
| Canal Telegram | `TELEGRAM_CHAT_ID` | `DEV_TELEGRAM_CHAT_ID` |
| Bot token | `TELEGRAM_BOT_TOKEN` | `DEV_TELEGRAM_BOT_TOKEN` |
| Lee historial JSON | Sí | No (historial vacío → no hay deduplicación) |
| Escribe historial JSON | Sí | No (`posted_bebe_deals.json` intacto) |

```bash
# Ejecutar en dev (requiere las vars DEV_* en el entorno)
source .env && python3 bebe/amazon_bebe_ofertas.py --dev
```

Las credenciales dev (`DEV_TELEGRAM_BOT_TOKEN`, `DEV_TELEGRAM_CHAT_ID`) están en `.env` y son las mismas que usa el proyecto `relases` para su canal de pruebas.

---

## Testing / Reseteo Manual

```bash
# Lanzar run manual en GitHub Actions
gh workflow run "Ofertas de Bebé"
gh run watch                  # Seguir progreso en tiempo real
gh run view --log-failed      # Ver logs si falla

# Ejecutar localmente en producción
source .env && python3 bebe/amazon_bebe_ofertas.py

# Ejecutar localmente en modo dev (no toca el JSON de prod)
source .env && python3 bebe/amazon_bebe_ofertas.py --dev

# Resetear todo el estado (vuelve a publicar desde cero)
rm bebe/posted_bebe_deals.json
git add bebe/posted_bebe_deals.json && git commit -m "chore: resetear estado" && git push

# Resetear solo el límite semanal de una categoría: editar JSON y borrar su entrada en _categorias_semanales
# Resetear categorías/títulos recientes: editar JSON y borrar _ultimas_categorias / _ultimos_titulos
```

## Dependencias

```bash
pip install -r requirements.txt      # Producción (requests, beautifulsoup4)
pip install -r requirements-dev.txt  # Desarrollo (pytest, pytest-cov)
```
