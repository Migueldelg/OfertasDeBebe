# 🍼 Ofertas de Bebé - Bot Automático de Amazon → Telegram

Bot que busca automáticamente las **mejores ofertas de productos de bebé** en Amazon.es y las publica en el canal de Telegram [@ofertasparaelbebe](https://t.me/ofertasparaelbebe).

---

## ¿Cómo funciona?

```
┌─────────────────────────────────────────────────────────────┐
│  1. El bot busca ofertas en Amazon en 12 categorías        │
│     (Pañales, Toallitas, Cremas, Leche, Juguetes, etc.)   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  2. De cada categoría, selecciona la mejor oferta          │
│     (mayor descuento, valoraciones altas, muchas ventas)   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  3. De todas las mejores, elige la de MAYOR DESCUENTO      │
│     (con prioridad a marcas: Dodot, Suavinex, etc.)        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Publica 1 oferta en Telegram con foto y enlace         │
└─────────────────────────────────────────────────────────────┘
```

---

## Sistema Anti-Repetición (Evita lo Mismo una y Otra Vez)

El bot es inteligente y **evita publicar lo mismo** mediante 4 filtros:

### 🔒 Anti-Duplicado (48 horas)
- Una vez publica un producto, **no lo vuelve a publicar en 48 horas**

### 🔄 Anti-Categoría Repetida
- Guarda las **últimas 4 categorías publicadas** y las evita si hay otras opciones
- **Excepción:** Pañales y Toallitas pueden repetirse (son compra frecuente)
- Si todas las opciones son recientes, publica la mejor igualmente

### 📄 Anti-Título Similar (Algunas Categorías)
- En Chupetes y Juguetes, evita títulos similares
- Ejemplo: Si publicó "Chupete Philips Pack 2", no publicará "Chupete Philips Pack 3"

### 📅 Límite Semanal (Algunas Categorías)
- Tronas, Cámaras de seguridad y Chupetes: **solo 1 oferta por semana**
- Productos que no son de compra recurrente

---

## Prioridad de Marcas (Lo Nuevo 🎉)

Cuando dos productos tienen el **MISMO descuento**, el bot prefiere estas marcas:

- 🟡 **Dodot**
- 🟡 **Suavinex**
- 🟡 **Baby Sebamed**
- 🟡 **Mustela**
- 🟡 **Waterwipes**

**Ejemplo:** Si hay 2 ofertas con 30% descuento (una de Dodot, otra de marca desconocida), se publica la de Dodot.

---

## Cómo Ejecutar

### Ejecución única (recomendado para cron/scheduler)
```bash
python3 amazon_bebe_ofertas.py
```

### Ejecución continua (cada 15 minutos)
```bash
python3 amazon_bebe_ofertas.py --continuo
```
Presiona `Ctrl+C` para detener.

---

## Qué Necesitas para Empezar

1. **Python 3** instalado
2. **Librerías Python:**
   ```bash
   pip install requests beautifulsoup4
   ```
3. **Token de Telegram Bot** (crea uno en @BotFather)
4. **ID del canal de Telegram** (ejemplo: `-1003703867125`)

---

## Configuración

Todas las configuraciones están en el archivo `amazon_bebe_ofertas.py`:

### Cambiar marcas prioritarias
```python
MARCAS_PRIORITARIAS = ["dodot", "suavinex", "baby sebamed", "mustela", "waterwipes"]
```

### Añadir una categoría nueva
```python
CATEGORIAS_BEBE = [
    {"nombre": "NombreCategoría", "emoji": "🆕", "url": "/s?k=termino+busqueda"},
    # ... más categorías
]
```

### Activar verificación de títulos en una categoría
```python
CATEGORIAS_VERIFICAR_TITULOS = ["Chupetes", "Juguetes", "Biberones"]
```

### Activar límite semanal en una categoría
```python
CATEGORIAS_LIMITE_SEMANAL = ["Tronas", "Camaras seguridad", "Chupetes"]
```

Para cambios más técnicos, ver **AGENTS.md** (referencia técnica).

---

## Archivos del Proyecto

```
OfertasDeBebe/
├── amazon_bebe_ofertas.py        ← El bot (único archivo que importa)
├── posted_bebe_deals.json        ← Estado (se crea automáticamente)
├── ofertas_bebe.log              ← Logs de ejecución
├── README.md                     ← Este archivo (guía general)
├── AGENTS.md                     ← Referencia técnica para IA
├── CLAUDE.md                     ← Para Claude AI
└── Como_usar_Ofertas_de_bebe.txt ← Manual antiguo
```

---

## Detalles Técnicos

- **Sin base de datos:** usa JSON local
- **Sin framework web:** solo Python + BeautifulSoup
- **1 oferta por ejecución:** para controlar frecuencia
- **Delays automáticos:** entre requests a Amazon (anti-bot)
- **Fallback automático:** si falla envío con foto, envía solo texto

---

## Precauciones

⚠️ **No hagas esto:**
- Eliminar los delays entre requests (Amazon te bloqueará)
- Hardcodear tokens en el código (usa variables de entorno)
- Cambiar selectores CSS sin saber qué haces (Amazon cambia su HTML frecuentemente)

---

## Solución de Problemas

### El bot no encuentra ofertas
- Revisar que las URLs de búsqueda en `CATEGORIAS_BEBE` sean válidas
- Verificar que Amazon no haya bloqueado las requests

### Se paró de repente
- Ver logs: `tail -f ofertas_bebe.log`
- Revisar que las credenciales de Telegram sean válidas

### Quiero resetear todo
```bash
rm posted_bebe_deals.json  # Borra el estado de todo
```

---

## Para Información Técnica Detallada

👉 Ver **AGENTS.md** para:
- Estructura de datos interna
- Lógica de selección de ofertas
- Selectores CSS
- Cómo modificar criterios de ordenamiento
- Funciones y sus líneas exactas

---

*Bot desarrollado para automatizar la búsqueda de las mejores ofertas de bebé. Publicado en [@ofertasparaelbebe](https://t.me/ofertasparaelbebe).*
