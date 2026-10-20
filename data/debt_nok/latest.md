# Informe Debt/NOK · 2026-10-20

**Estado oficial: Normal.** Sin configuración activa de crisis; vigilancia estructural normal

El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK.

**Actualizado en Oslo:** 2026-10-20 14:20. **Último dato oficial disponible:** 2026-10-19. **Bloque oficial más retrasado:** URR (15 días hábiles).

## Frescura oficial de los bloques

| Bloque | Datos a | Retraso aproximado | Estado |
|---|---|---:|---|
| URP | 2026-10-16 | 1 día hábil | Actualizado |
| URR | 2026-09-28 | 15 días hábiles | Obsoleto |
| DSS | 2026-10-16 | 1 día hábil | Actualizado |
| NKS | 2026-10-09 | 6 días hábiles | Obsoleto |
| NRS | 2026-10-09 | 6 días hábiles | Obsoleto |

## Panel oficial de bloques

| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |
|---|---:|---|---|---:|---:|
| URP · Rechazo USA | 0.00 | inactive | 2026-10-16 | 0.00 | +0.00 |
| URR · Persistencia USA | 0.00 | inactive | 2026-09-28 | 0.00 | +0.00 |
| DSS · Escasez de dólares | 0.00 | inactive | 2026-10-16 | 0.00 | +0.00 |
| NKS · Estrés NOK | 7.04 | normal | 2026-10-09 | 10.05 | -3.01 |
| NRS · Reversión NOK | 0.00 | inactive | 2026-10-09 | 0.00 | +0.00 |

## Variables discriminantes oficiales

- Treasury 30 años, cambio 10 sesiones: **-18.0 pb**.
- Dólar amplio, caída 10 sesiones: **0.31 %**.
- VIX: **19.99**.
- EUR/NOK, cambio 20 sesiones: **-0.59 %**.
- Debilidad NOK frente a SEK, 20 sesiones: **-0.14 %**.
- Residual NOK: **0.50σ**.
- Norway–Bund, cambio 20 sesiones: **9.8 pb**.

## Lectura operativa oficial

- Ningún bloque operativo supera sus umbrales de vigilancia.

## Lectura rápida provisional

**Normal.** La vía rápida provisional no eleva el nivel de la lectura oficial.

La vía rápida usa proxies primarios o secundarios expresamente identificados y validados. No confirma por sí sola un cambio de régimen; la lectura oficial conserva prioridad.

| Bloque | Oficial | Provisional | Δ | Estado provisional | Datos provisionales a |
|---|---:|---:|---:|---|---|
| URP | 0.00 | 0.00 | 0.00 | inactive | 2026-10-19 |
| URR | 0.00 | 0.00 | 0.00 | inactive | 2026-09-28 |
| DSS | 0.00 | 0.00 | 0.00 | inactive | 2026-10-19 |
| NKS | 7.04 | 7.04 | 0.00 | normal | 2026-10-09 |
| NRS | 0.00 | 0.00 | 0.00 | inactive | 2026-10-09 |

### Puentes de datos

| Serie | Estado | Oficial hasta | Proxy hasta | Extensión hasta | Correlación | Error medio |
|---|---|---|---|---|---:|---:|
| DEXUSEU | expired | 2026-10-09 | 2026-10-19 | — | 0.647 | 0.203 pp |
| DEXNOUS | expired | 2026-10-09 | 2026-10-19 | — | 0.793 | 0.187 pp |
| DEXSDUS | expired | 2026-10-09 | 2026-10-19 | — | 0.636 | 0.316 pp |
| DTWEXBGS | active | 2026-10-16 | 2026-10-19 | 2026-10-19 | 0.600 | 0.194 pp |
| DCOILBRENTEU | active | 2026-10-14 | 2026-10-19 | 2026-10-19 | 0.765 | 1.917 pp |

**Fuentes rápidas no disponibles:**
- CME_WTI_SETTLEMENT: CME WTI settlements unavailable: 2026-10-02: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT?tradeDate=10%2F02%2F2026: HTTP Error 403: Forbidden
- EIA_WTI_SPOT: https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=DEMO_KEY&frequency=daily&data[0]=value&facets[series][]=RWTC&start=2025-06-07&sort[0][column]=period&sort[0][direction]=asc&offset=0&length=5000: The read operation timed out

## Método y límites

El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque oficial usa su propia fecha completa de datos; los datos ausentes no se imputan como cero.

La vía rápida provisional utiliza únicamente rendimientos de proxies primarios o secundarios expresamente identificados y validados, reanclados al último nivel oficial. No sobrescribe historia, caduca automáticamente y nunca sustituye la lectura oficial.

La frescura no altera scores, pesos ni umbrales. Una señal provisional divergente solicita revisión humana; sólo la publicación oficial puede confirmarla dentro del modelo operativo.

Cadencia: Lunes, 07:30 UTC para el informe completo; Martes a viernes, 07:00 UTC para comprobaciones intermedias y alertas materiales.
