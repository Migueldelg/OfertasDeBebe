# Ofertas de Bebé - Bot Automático de Amazon → Telegram

Bot que busca automáticamente las **mejores ofertas de productos de bebé** en Amazon.es y las publica en el canal de Telegram [@ofertasparaelbebe](https://t.me/ofertasparaelbebe).

Corre en **GitHub Actions** cada 30 minutos, sin necesidad de servidor propio.

---

## ¿Cómo funciona?

```
1. Busca ofertas en Amazon en 12 categorías (Pañales, Toallitas, Cremas, Leche, Juguetes, etc.)
                          ↓
2. De cada categoría, selecciona la mejor oferta (mayor descuento, valoraciones altas)
                          ↓
3. De todas las mejores, elige la de MAYOR DESCUENTO (con prioridad a marcas conocidas)
                          ↓
4. Publica 1 oferta en Telegram con foto y enlace
```

---

## Sistema Anti-Repetición

El bot evita publicar lo mismo mediante 4 filtros:

- **Anti-ASIN (48h):** No repite el mismo producto en 48 horas
- **Anti-Categoría:** Evita las últimas 4 categorías publicadas (excepto Pañales/Toallitas)
- **Anti-Título Similar:** En Chupetes y Juguetes, evita títulos con >50% palabras comunes
- **Límite Semanal:** Tronas, Cámaras de seguridad y Chupetes: solo 1 oferta por semana

---

## Prioridad de Marcas

Cuando dos productos tienen el **mismo descuento**, el bot prefiere: Dodot, Suavinex, Baby Sebamed, Mustela, Waterwipes.

---

## Configuración

Todas las configuraciones están en `amazon_bebe_ofertas.py`:

| Constante | Qué controla |
|-----------|-------------|
| `CATEGORIAS_BEBE` (~línea 62) | Categorías a buscar |
| `MARCAS_PRIORITARIAS` (~línea 65) | Marcas preferidas en igualdad de descuento |
| `CATEGORIAS_VERIFICAR_TITULOS` (~línea 56) | Categorías con anti-título-similar |
| `CATEGORIAS_LIMITE_SEMANAL` (~línea 59) | Categorías con límite de 1/semana |

Para detalles técnicos, ver **AGENTS.md**.

---

## Archivos del Proyecto

```
OfertasDeBebe/
├── amazon_bebe_ofertas.py        ← El bot
├── posted_bebe_deals.json        ← Estado anti-duplicados (versionado para persistir entre runs)
├── requirements.txt              ← Dependencias Python
├── .github/workflows/ofertas.yml ← Workflow de GitHub Actions (cada 30 min)
├── .gitignore
├── README.md
├── AGENTS.md                     ← Referencia técnica para IA
└── CLAUDE.md                     ← Referencia rápida para Claude
```

---

## GitHub Actions

El bot corre automáticamente en GitHub Actions cada 30 minutos. Los secretos `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` están configurados en *Settings → Secrets and variables → Actions*.

Al final de cada run, si se publicó una oferta nueva, el workflow hace commit de `posted_bebe_deals.json` de vuelta al repo para persistir el estado.

Los logs de cada run están disponibles en la pestaña *Actions* del repo durante 90 días.

### Ejecución manual

```bash
gh workflow run "Ofertas de Bebé"
gh run watch  # Seguir progreso en tiempo real
```

---

## Solución de Problemas

### El bot no encuentra ofertas
- Revisar que las URLs en `CATEGORIAS_BEBE` sean válidas en Amazon.es
- Comprobar si Amazon ha cambiado los selectores CSS (ver AGENTS.md)

### No llega mensaje a Telegram
- Verificar que los secrets `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` están correctamente configurados
- Revisar los logs del último run en GitHub Actions

### Resetear el estado
```bash
# Borrar el estado: el bot volverá a publicar desde cero
rm posted_bebe_deals.json
git add posted_bebe_deals.json && git commit -m "chore: resetear estado" && git push
```

---

## Precauciones

- No eliminar los delays entre requests (Amazon bloqueará las peticiones)
- No cambiar selectores CSS sin saber qué haces (Amazon cambia su HTML frecuentemente)
- Las credenciales van en GitHub Secrets, nunca en el código

---

*Publicado en [@ofertasparaelbebe](https://t.me/ofertasparaelbebe).*
