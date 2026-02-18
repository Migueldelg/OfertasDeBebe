# 🎮 Canal PS4/PS5 - Buscador de Ofertas

Script para obtener las mejores ofertas de videojuegos y accesorios PS4/PS5 de Amazon.es y publicarlas en un canal de Telegram.

## Estructura

```
ps/
├── amazon_ps_ofertas.py           ← Script principal
├── posted_ps_deals.json           ← Estado anti-duplicados (actualizado automáticamente)
├── ofertas_ps.log                 ← Logs de ejecución
├── README.md                      ← Este archivo
└── tests/
    └── test_amazon_ps_ofertas.py  ← 59 tests automatizados
```

## Características

✅ **Videojuegos priorizados** - Siempre publica juegos PS4/PS5 antes que accesorios
✅ **Agrupamiento de variantes** - Automáticamente agrupa PS4/PS5 en un solo mensaje con links paralelos
✅ **Anti-duplicados 48h** - No repite el mismo ASIN en 48 horas (incluyendo variantes)
✅ **Anti-títulos similares** - Evita publicar juegos similares repetidamente
✅ **Modo desarrollo** - Publica en canal de pruebas sin modificar el JSON
✅ **Tests completos** - 79 tests que cubren toda la lógica incluyendo variantes

## Configuración

### Credenciales de Telegram

Necesitas dos conjuntos de credenciales:

1. **Producción** (publicar en el canal real):
   ```bash
   export TELEGRAM_PS_BOT_TOKEN=8542903683:AAFcIbXqweq8b4Sqo2c7eaKsgkneZcivfio
   export TELEGRAM_PS_CHAT_ID=1003885398555
   ```

2. **Desarrollo** (publicar en canal de pruebas, sin modificar JSON):
   ```bash
   export DEV_TELEGRAM_PS_BOT_TOKEN=...
   export DEV_TELEGRAM_PS_CHAT_ID=...
   ```

Guarda estas variables en tu `.env` local:
```bash
source .env
```

## Ejecución

### Modo Manual (una sola vez)

```bash
# Publicar en el canal de producción
source .env && python3 ps/amazon_ps_ofertas.py

# Publicar en canal de pruebas (no modifica posted_ps_deals.json)
source .env && python3 ps/amazon_ps_ofertas.py --dev
```

### Modo Continuo (cada 15 minutos)

```bash
source .env && python3 ps/amazon_ps_ofertas.py --continuo
```

### Tests

```bash
# Ejecutar todos los tests
python3 -m pytest ps/tests/ -v

# Ver cobertura
python3 -m pytest ps/tests/ --cov=ps.amazon_ps_ofertas --cov-report=term-missing

# Ejecutar un test específico
python3 -m pytest ps/tests/test_amazon_ps_ofertas.py::TestObtenerPrioridadMarca -v
```

## Lógica de Selección

```
1. Para cada categoría (videojuegos primero, luego accesorios):
   ├─ Obtener productos de Amazon
   ├─ Filtrar solo los que tienen descuento
   └─ Elegir el mejor según: descuento ↓ → marca_prioritaria ↓ → valoraciones ↓ → ventas ↓

2. Agrupar variantes del mismo producto (ej: FIFA 26 PS4 ↔ FIFA 26 PS5)
   ├─ Representante: producto con mayor descuento
   └─ Variantes adicionales: guardadas para mostrar en Telegram

3. De todos los mejores por categoría:
   ├─ Prefiere videojuegos sobre accesorios
   ├─ Evita repetir las últimas 4 categorías (si hay alternativas)
   ├─ No republica ASINs en <48h (incluyendo variantes)
   └─ Para Juegos PS4/PS5: evita títulos similares a los últimos publicados

4. Publicar en Telegram con formato especial si hay variantes
5. Guardar estado (ASINs de todas las variantes)
```

### Formato Telegram con Variantes

Cuando se detectan variantes (ej: PS5 vs PS4), el mensaje muestra **múltiples links paralelos**:

```
🎮 OFERTA JUEGOS PS5 🎮

📦 FIFA 26 PS5

💰 39,99€ <s>69,99€</s> (-43%)
💰 34,99€ <s>58,99€</s> (-40%) (PS4)
```

**Características:**
- ✅ Ambos precios son **clickeables** (no hay "También disponible")
- ✅ Identificadores automáticos: `(PS4)`, `(PS5)`, `(AZUL)`, etc.
- ✅ Precios anteriores tachados en ambas opciones
- ✅ Descuentos mostrados en ambas variantes

**Formato original sin variantes (preservado):**
```
🎮 OFERTA JUEGOS PS5 🎮

📦 Mando DualSense

💰 Precio: 74,99€ → 59,99€ (-20%)

🛒 Ver en Amazon
```

## Categorías

### Videojuegos (Priorizados ⭐)
- 🎮 Juegos PS5 → `/s?k=juegos+ps5`
- 🎮 Juegos PS4 → `/s?k=juegos+ps4`

### Accesorios
- 🕹️ Mandos PS5 → `/s?k=mando+dualsense+ps5`
- 🕹️ Mandos PS4 → `/s?k=mando+dualshock+ps4`
- 🎧 Auriculares gaming → `/s?k=auriculares+gaming+ps4+ps5`
- 💳 Tarjetas PSN → `/s?k=tarjeta+psn+playstation`
- ⚙️ Accesorios PS5 → `/s?k=accesorios+ps5`
- ⚙️ Accesorios PS4 → `/s?k=accesorios+ps4`

## Marcas Prioritarias

Cuando hay igualdad de descuento, se prefieren estas marcas:
- `sony`
- `playstation`
- `nacon`
- `thrustmaster`
- `razer`
- `hyperx`

## Archivo de Estado: `posted_ps_deals.json`

Estructura del JSON que mantiene el historial:

```json
{
  "_ultimas_categorias": ["Juegos PS5", "Mandos PS5", "Accesorios PS5", "Juegos PS4"],
  "_ultimos_titulos": ["Juego PS5 Elden Ring...", "Juego PS5 The Last..."],
  "_categorias_semanales": {},
  "B08XYZ123": "2025-02-17T10:30:00",
  "B07ABC456": "2025-02-16T18:45:00"
}
```

- **`_ultimas_categorias`**: Últimas 4 categorías publicadas (para evitar repetir)
- **`_ultimos_titulos`**: Últimos 4 títulos de juegos (para evitar similares)
- **`_categorias_semanales`**: Timestamps de últimas publicaciones por categoría (no aplica en PS)
- **`ASIN`**: Timestamp ISO de cuándo se publicó (expirado después de 48h)

## Modo DEV vs PROD

| Comportamiento | Producción | Dev (`--dev`) |
|---|---|---|
| Canal Telegram | `TELEGRAM_PS_CHAT_ID` | `DEV_TELEGRAM_PS_CHAT_ID` |
| Bot token | `TELEGRAM_PS_BOT_TOKEN` | `DEV_TELEGRAM_PS_BOT_TOKEN` |
| Lee historial JSON | ✅ Sí | ❌ No (vacío) |
| Escribe historial JSON | ✅ Sí | ❌ No (sin cambios) |
| Deduplicación | ✅ Sí | ❌ No (puede repetir) |

Ideal para **probar cambios sin contaminar el historial de producción**.

## Resetear Estado

```bash
# Resetear TODO el historial (volverá a publicar desde cero)
rm ps/posted_ps_deals.json
git add ps/posted_ps_deals.json && git commit -m "chore: resetear estado PS" && git push

# Resetear solo las últimas categorías: editar JSON manualmente
# Resetear solo los títulos recientes: editar JSON manualmente
```

## Logs

Los logs se guardan en `ps/ofertas_ps.log` con rotación diaria (conserva últimos 5 días).

```bash
# Ver logs en tiempo real
tail -f ps/ofertas_ps.log

# Ver último ciclo
tail -50 ps/ofertas_ps.log
```

## Diferencias con el canal de Bebé

| Aspecto | Bebé | PS |
|---|---|---|
| Priorización | Categórica (Pañales/Toallitas sin repetición) | Videojuegos siempre |
| Límite semanal | ✅ Tronas, Cámaras, Chupetes, Vajilla | ❌ Ninguno |
| Videojuegos | ❌ No aplica | ✅ Priorizados |
| Anti-títulos similares | Chupetes, Juguetes | Juegos PS5, Juegos PS4 |
| Agrupamiento de variantes | ✅ Ambos canales | ✅ Ambos canales |
| Tests | 84 tests | 79 tests |

## Próximos Pasos (GitHub Actions)

Cuando estés listo para programar automáticamente:

1. Crear `.github/workflows/ofertas-ps.yml` (similar a `ofertas.yml`)
2. Añadir secrets en GitHub:
   - `TELEGRAM_PS_BOT_TOKEN`
   - `TELEGRAM_PS_CHAT_ID`
3. Configurar schedule: `0 */30 * * *` (cada 30 minutos)
4. Git pull --rebase para evitar conflictos de concurrencia

## Testing

Todos los tests usan mocks y fixtures, sin acceder a Amazon ni Telegram:

- ✅ **Funciones puras**: normalización, similitud, prioridades
- ✅ **I/O con mocks**: Telegram, archivos JSON
- ✅ **Parsing HTML**: extracción de productos
- ✅ **Lógica de selección**: priorización de videojuegos, anti-duplicados

```bash
# Cobertura detallada
python3 -m pytest ps/tests/ -v --cov=ps.amazon_ps_ofertas --cov-report=html
# Abrir htmlcov/index.html
```

## Troubleshooting

### Error: "Credenciales de Telegram no configuradas"
```bash
# Asegúrate de que las variables están en el entorno:
echo $TELEGRAM_PS_BOT_TOKEN
echo $TELEGRAM_PS_CHAT_ID

# O en modo dev:
echo $DEV_TELEGRAM_PS_BOT_TOKEN
echo $DEV_TELEGRAM_PS_CHAT_ID
```

### Amazon bloqueó la IP
Si obtiene errores de conexión, intenta:
```bash
# Limpiar historial de reintentos
rm ps/ofertas_ps.log
```

### Los tests fallan
```bash
# Asegúrate de que el módulo se importa correctamente
python3 -c "import ps.amazon_ps_ofertas; print('OK')"

# Ejecuta en verbose para más detalles
python3 -m pytest ps/tests/ -vv
```

---

**Creado con ❤️ en Fase 3 del Plan PS**
