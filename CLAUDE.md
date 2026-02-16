# CLAUDE.md - Referencia Rápida para Claude AI

**Ver documentación completa:**
- 📖 **README.md** → Guía general "¿Cómo funciona?"
- 🔧 **AGENTS.md** → Referencia técnica completa (estructura de datos, funciones, selectores CSS, líneas exactas)

---

## Resumen Ejecutivo

- **Qué:** Bot que busca las mejores ofertas de bebé en Amazon.es → publica en Telegram
- **Dónde:** Archivo único `amazon_bebe_ofertas.py`
- **Cuándo:** Una vez por ejecución (o cada 15 min en modo continuo)
- **Cómo:** Busca 12 categorías → elige la mejor de cada → publica la mejor global

---

## Constantes de Configuración

```python
CATEGORIAS_BEBE                    # Línea ~62 - Categorías a buscar
CATEGORIAS_VERIFICAR_TITULOS       # Línea ~56 - Evitar títulos similares
CATEGORIAS_LIMITE_SEMANAL          # Línea ~59 - Solo 1x por semana
MARCAS_PRIORITARIAS                # Línea ~65 - Marcas en igualdad de descuento
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  # Línea ~61-62 - Leen de env vars / GitHub Secrets
```

---

## Sistema Anti-Repetición (4 Mecanismos)

1. **Anti-ASIN (48h):** No repite el mismo producto en 48 horas
2. **Anti-Categoría:** Evita las últimas 4 categorías (excepto Pañales/Toallitas)
3. **Anti-Título Similar:** Para Chupetes/Juguetes, evita títulos con >50% palabras comunes
4. **Límite Semanal:** Tronas/Cámaras/Chupetes solo 1 vez por semana

---

## Prioridad de Marcas (Lo Nuevo)

Cuando **igual descuento**, prefiere: `dodot`, `suavinex`, `baby sebamed`, `mustela`, `waterwipes`

---

## Lógica de Selección

```
Para cada categoría:
  1. Obtener ofertas de Amazon
  2. Ordenar: descuento ↓ → marca_prioritaria ↓ → valoraciones ↓ → ventas ↓
  3. Tomar la mejor no duplicada

De todas las mejores:
  1. Ordenar por: descuento ↓ → marca_prioritaria ↓
  2. Evitar últimas 4 categorías (si hay alternativas)
  3. Publicar en Telegram
```

---

## Ejecución

El bot corre en **GitHub Actions** cada 30 minutos automáticamente.

```bash
gh workflow run "Ofertas de Bebé"   # Lanzar manualmente
gh run watch                        # Ver progreso
python3 amazon_bebe_ofertas.py      # Ejecutar local (requiere env vars)
```

---

## Cambios Comunes

| Tarea | Ubicación |
|-------|-----------|
| Añadir categoría | `CATEGORIAS_BEBE` línea ~62 |
| Cambiar marcas prioritarias | `MARCAS_PRIORITARIAS` línea ~65 |
| Cambiar ventana anti-duplicados | `timedelta(hours=48)` en `load_posted_deals()` |
| Cambiar frecuencia del schedule | `cron:` en `.github/workflows/ofertas.yml` |
| Cambiar formato Telegram | Función `format_telegram_message()` |
| Cambiar selectores CSS | Función `extraer_productos_busqueda()` |
| Credenciales Telegram | GitHub Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |

---

**Más detalles técnicos:** Ver **AGENTS.md**
