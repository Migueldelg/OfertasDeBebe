# AGENTS.md - Referencia Técnica para Agentes IA

## Contexto Rápido

Bot de scraping que:
1. Busca ofertas en Amazon.es por categorías de bebé
2. Selecciona la mejor oferta global (mayor descuento)
3. La publica en un canal de Telegram
4. Evita duplicados mediante un JSON de tracking

**Archivo principal único:** `amazon_bebe_ofertas.py`

---

## Constantes de Configuración Clave

| Constante | Línea | Descripción |
|-----------|-------|-------------|
| `CATEGORIAS_BEBE` | ~62 | Lista de categorías a buscar |
| `CATEGORIAS_VERIFICAR_TITULOS` | ~56 | Categorías donde se comparan títulos para evitar similares |
| `CATEGORIAS_LIMITE_SEMANAL` | ~59 | Categorías que solo se publican una vez por semana (Tronas, Cámaras seguridad, Chupetes) |
| `MARCAS_PRIORITARIAS` | ~65 | Marcas preferidas cuando hay igualdad de descuento |

---

## Tareas Comunes

### Añadir nueva categoría

Editar `CATEGORIAS_BEBE` (línea ~62):
```python
{"nombre": "NombreVisible", "emoji": "🆕", "url": "/s?k=busqueda+amazon"}
```

### Activar verificación de títulos en una categoría

Editar `CATEGORIAS_VERIFICAR_TITULOS` (línea ~56):
```python
CATEGORIAS_VERIFICAR_TITULOS = ["Chupetes", "Juguetes", "NuevaCategoria"]
```

### Activar límite semanal en una categoría

Editar `CATEGORIAS_LIMITE_SEMANAL` (línea ~59):
```python
CATEGORIAS_LIMITE_SEMANAL = ["Tronas", "Camaras seguridad", "Chupetes"]
```

> Los nombres deben coincidir exactamente con el campo `nombre` en `CATEGORIAS_BEBE`.

### Añadir o modificar marcas prioritarias

Editar `MARCAS_PRIORITARIAS` (línea ~65):
```python
MARCAS_PRIORITARIAS = ["dodot", "suavinex", "baby sebamed", "mustela", "waterwipes"]
```

Estas marcas se priorizan cuando hay **igualdad de descuento**. La búsqueda es case-insensitive y busca si el nombre de la marca aparece en el título del producto.

### Cambiar frecuencia en modo continuo

`time.sleep(900)` en `main()` — valor en segundos.

### Cambiar ventana anti-duplicados de ASINs

`timedelta(hours=48)` en `load_posted_deals()`.

### Modificar formato del mensaje de Telegram

Función `format_telegram_message()`.

### Cambiar criterio de ordenación de ofertas

En `buscar_y_publicar_ofertas()`:
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

Parámetro `umbral` en `titulos_similares()` (por defecto `0.5` = 50%).

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

### Archivo JSON (`posted_bebe_deals.json`)
```json
{
    "_ultimas_categorias": ["Juguetes", "Panales", "Chupetes", "Tronas"],
    "_ultimos_titulos": ["Philips Avent Chupete ultra soft...", "Fisher-Price..."],
    "_categorias_semanales": {
        "Tronas": "2024-01-15T10:30:00",
        "Camaras seguridad": "2024-01-10T08:00:00"
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

3. De todas las mejores por categoría (ordenadas por descuento):
   └─ Para cada una:
      ├─ ¿Categoría en las últimas 4 publicadas? → Siguiente (si hay más opciones)
      └─ ✓ Seleccionar para publicar

4. Si todas son de categorías recientes → publicar la de mayor descuento igualmente

5. Publicar en Telegram y guardar estado
```

---

## Funciones Importantes

| Función | Descripción | Línea |
|---------|-------------|-------|
| `obtener_prioridad_marca()` | Detecta si un título contiene una marca prioritaria; retorna 1 (prioritaria) o 0 | ~189 |
| `titulo_similar_a_recientes()` | Verifica similitud con últimos 4 títulos para evitar repeticiones | ~175 |
| `titulos_similares()` | Compara dos títulos con umbral configurable (default 50%) | ~153 |
| `normalizar_titulo()` | Extrae palabras clave de un título para comparación | ~138 |

---

## Selectores CSS (Amazon)

Si Amazon cambia su HTML, estos son los selectores a revisar en `extraer_productos_busqueda()`:

| Elemento | Selector |
|----------|----------|
| Contenedor producto | `[data-component-type="s-search-result"]` |
| Título | `h2 a span` |
| Precio actual | `.a-price .a-offscreen` |
| Precio anterior (tachado) | `.a-price[data-a-strike="true"] .a-offscreen` |
| Imagen | `img.s-image` |
| Valoraciones | `.a-size-base.s-underline-text` |
| Ventas | `.a-size-base.a-color-secondary` |

---

## Precauciones

1. **Nombres de categoría:** deben coincidir exactamente entre `CATEGORIAS_BEBE`, `CATEGORIAS_VERIFICAR_TITULOS` y `CATEGORIAS_LIMITE_SEMANAL`
2. **Anti-bot:** no eliminar los delays entre requests (`time.sleep` en `obtener_pagina()`)
3. **Selectores:** Amazon cambia su HTML frecuentemente; si el scraper falla, revisar los selectores
4. **Credenciales:** no hardcodear tokens en el código; usar variables de entorno
5. **Rate limits:** Telegram limita mensajes por segundo; no modificar el flujo para publicar varios a la vez

---

## Testing / Reseteo Manual

```bash
# Lanzar run manual en GitHub Actions
gh workflow run "Ofertas de Bebé"
gh run watch                  # Seguir progreso en tiempo real
gh run view --log-failed      # Ver logs si falla

# Ejecutar localmente (requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en entorno)
python3 amazon_bebe_ofertas.py

# Resetear todo el estado (vuelve a publicar desde cero)
rm posted_bebe_deals.json
git add posted_bebe_deals.json && git commit -m "chore: resetear estado" && git push

# Resetear solo el límite semanal de una categoría: editar JSON y borrar su entrada en _categorias_semanales
# Resetear categorías/títulos recientes: editar JSON y borrar _ultimas_categorias / _ultimos_titulos
```

## Dependencias

```bash
pip install -r requirements.txt
```

Sin base de datos, sin framework web, sin tests automatizados.
