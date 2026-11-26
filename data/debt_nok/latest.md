# Informe Debt/NOK · 2026-11-26

**Estado oficial: Normal.** Sin configuración activa de crisis; vigilancia estructural normal

El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK.

**Actualizado en Oslo:** 2026-11-26 18:23. **Último dato oficial disponible:** 2026-11-25. **Bloque oficial más retrasado:** URR (42 días hábiles).

## Frescura oficial de los bloques

| Bloque | Datos a | Retraso aproximado | Estado |
|---|---|---:|---|
| URP | 2026-11-20 | 3 días hábiles | Retrasado |
| URR | 2026-09-28 | 42 días hábiles | Obsoleto |
| DSS | 2026-11-20 | 3 días hábiles | Retrasado |
| NKS | 2026-11-17 | 6 días hábiles | Obsoleto |
| NRS | 2026-11-17 | 6 días hábiles | Obsoleto |

## Panel oficial de bloques

| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |
|---|---:|---|---|---:|---:|
| URP · Rechazo USA | 0.00 | inactive | 2026-11-20 | 0.00 | +0.00 |
| URR · Persistencia USA | 0.00 | inactive | 2026-09-28 | 0.00 | +0.00 |
| DSS · Escasez de dólares | 0.00 | inactive | 2026-11-20 | 0.00 | +0.00 |
| NKS · Estrés NOK | 1.82 | normal | 2026-11-17 | 0.66 | +1.16 |
| NRS · Reversión NOK | 0.00 | inactive | 2026-11-17 | 0.00 | +0.00 |

## Variables discriminantes oficiales

- Treasury 30 años, cambio 10 sesiones: **6.0 pb**.
- Dólar amplio, caída 10 sesiones: **-1.72 %**.
- VIX: **35.89**.
- EUR/NOK, cambio 20 sesiones: **0.29 %**.
- Debilidad NOK frente a SEK, 20 sesiones: **0.16 %**.
- Residual NOK: **-0.86σ**.
- Norway–Bund, cambio 20 sesiones: **-7.1 pb**.

## Lectura operativa oficial

- Ningún bloque operativo supera sus umbrales de vigilancia.

## Lectura rápida provisional

**Normal.** La vía rápida provisional no eleva el nivel de la lectura oficial.

La vía rápida usa proxies primarios o secundarios expresamente identificados y validados. No confirma por sí sola un cambio de régimen; la lectura oficial conserva prioridad.

| Bloque | Oficial | Provisional | Δ | Estado provisional | Datos provisionales a |
|---|---:|---:|---:|---|---|
| URP | 0.00 | 0.00 | 0.00 | inactive | 2026-11-25 |
| URR | 0.00 | 0.00 | 0.00 | inactive | 2026-09-28 |
| DSS | 0.00 | 0.00 | 0.00 | inactive | 2026-11-25 |
| NKS | 1.82 | 24.59 | 22.77 | normal | 2026-11-24 |
| NRS | 0.00 | 0.00 | 0.00 | inactive | 2026-11-24 |

### Puentes de datos

| Serie | Estado | Oficial hasta | Proxy hasta | Extensión hasta | Correlación | Error medio |
|---|---|---|---|---|---:|---:|
| DEXUSEU | active | 2026-11-20 | 2026-11-26 | 2026-11-26 | 0.607 | 0.205 pp |
| DEXNOUS | active | 2026-11-20 | 2026-11-26 | 2026-11-26 | 0.683 | 0.263 pp |
| DEXSDUS | active | 2026-11-20 | 2026-11-26 | 2026-11-26 | 0.695 | 0.256 pp |
| DTWEXBGS | active | 2026-11-20 | 2026-11-26 | 2026-11-26 | 0.636 | 0.174 pp |
| DCOILBRENTEU | active | 2026-11-17 | 2026-11-24 | 2026-11-24 | 0.759 | 1.848 pp |

**Fuentes rápidas no disponibles:**
- CME_WTI_SETTLEMENT: CME WTI settlements unavailable: 2026-11-09: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT?tradeDate=11%2F09%2F2026: HTTP Error 403: Forbidden
- EIA_WTI_SPOT: https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=DEMO_KEY&frequency=daily&data[0]=value&facets[series][]=RWTC&start=2025-07-14&sort[0][column]=period&sort[0][direction]=asc&offset=0&length=5000: The read operation timed out

## Método y límites

El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque oficial usa su propia fecha completa de datos; los datos ausentes no se imputan como cero.

La vía rápida provisional utiliza únicamente rendimientos de proxies primarios o secundarios expresamente identificados y validados, reanclados al último nivel oficial. No sobrescribe historia, caduca automáticamente y nunca sustituye la lectura oficial.

La frescura no altera scores, pesos ni umbrales. Una señal provisional divergente solicita revisión humana; sólo la publicación oficial puede confirmarla dentro del modelo operativo.

Cadencia: Lunes, 07:30 UTC para el informe completo; Martes a viernes, 07:00 UTC para comprobaciones intermedias y alertas materiales.
