# Informe Debt/NOK · 2026-11-13

**Estado oficial: Normal.** Sin configuración activa de crisis; vigilancia estructural normal

El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK.

**Actualizado en Oslo:** 2026-11-13 15:57. **Último dato oficial disponible:** 2026-11-12. **Bloque oficial más retrasado:** URR (33 días hábiles).

## Frescura oficial de los bloques

| Bloque | Datos a | Retraso aproximado | Estado |
|---|---|---:|---|
| URP | 2026-11-06 | 4 días hábiles | Obsoleto |
| URR | 2026-09-28 | 33 días hábiles | Obsoleto |
| DSS | 2026-11-06 | 4 días hábiles | Obsoleto |
| NKS | 2026-11-06 | 4 días hábiles | Obsoleto |
| NRS | 2026-11-06 | 4 días hábiles | Obsoleto |

## Panel oficial de bloques

| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |
|---|---:|---|---|---:|---:|
| URP · Rechazo USA | 0.00 | inactive | 2026-11-06 | 0.00 | +0.00 |
| URR · Persistencia USA | 0.00 | inactive | 2026-09-28 | 0.00 | +0.00 |
| DSS · Escasez de dólares | 0.00 | inactive | 2026-11-06 | 0.00 | +0.00 |
| NKS · Estrés NOK | 0.00 | normal | 2026-11-06 | 0.00 | +0.00 |
| NRS · Reversión NOK | 0.00 | inactive | 2026-11-06 | 0.00 | +0.00 |

## Variables discriminantes oficiales

- Treasury 30 años, cambio 10 sesiones: **-7.0 pb**.
- Dólar amplio, caída 10 sesiones: **-0.46 %**.
- VIX: **25.64**.
- EUR/NOK, cambio 20 sesiones: **-1.77 %**.
- Debilidad NOK frente a SEK, 20 sesiones: **-0.11 %**.
- Residual NOK: **-1.88σ**.
- Norway–Bund, cambio 20 sesiones: **-3.7 pb**.

## Lectura operativa oficial

- Ningún bloque operativo supera sus umbrales de vigilancia.

## Lectura rápida provisional

**Normal.** La vía rápida provisional no eleva el nivel de la lectura oficial.

La vía rápida usa proxies primarios o secundarios expresamente identificados y validados. No confirma por sí sola un cambio de régimen; la lectura oficial conserva prioridad.

| Bloque | Oficial | Provisional | Δ | Estado provisional | Datos provisionales a |
|---|---:|---:|---:|---|---|
| URP | 0.00 | 0.00 | 0.00 | inactive | 2026-11-06 |
| URR | 0.00 | 0.00 | 0.00 | inactive | 2026-09-28 |
| DSS | 0.00 | 0.00 | 0.00 | inactive | 2026-11-06 |
| NKS | 0.00 | 0.00 | 0.00 | normal | 2026-11-06 |
| NRS | 0.00 | 0.00 | 0.00 | inactive | 2026-11-06 |

### Puentes de datos

| Serie | Estado | Oficial hasta | Proxy hasta | Extensión hasta | Correlación | Error medio |
|---|---|---|---|---|---:|---:|
| DEXUSEU | rejected | 2026-11-06 | 2026-11-13 | — | 0.576 | 0.215 pp |
| DEXNOUS | rejected | 2026-11-06 | 2026-11-13 | — | 0.638 | 0.255 pp |
| DEXSDUS | active | 2026-11-06 | 2026-11-13 | 2026-11-13 | 0.630 | 0.278 pp |
| DTWEXBGS | expired | 2026-11-06 | 2026-11-13 | — | 0.627 | 0.181 pp |
| DCOILBRENTEU | active | 2026-11-11 | 2026-11-12 | 2026-11-12 | 0.750 | 1.968 pp |

**Fuentes rápidas no disponibles:**
- CME_WTI_SETTLEMENT: CME WTI settlements unavailable: 2026-10-26: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT?tradeDate=10%2F26%2F2026: HTTP Error 403: Forbidden

## Método y límites

El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque oficial usa su propia fecha completa de datos; los datos ausentes no se imputan como cero.

La vía rápida provisional utiliza únicamente rendimientos de proxies primarios o secundarios expresamente identificados y validados, reanclados al último nivel oficial. No sobrescribe historia, caduca automáticamente y nunca sustituye la lectura oficial.

La frescura no altera scores, pesos ni umbrales. Una señal provisional divergente solicita revisión humana; sólo la publicación oficial puede confirmarla dentro del modelo operativo.

Cadencia: Lunes, 07:30 UTC para el informe completo; Martes a viernes, 07:00 UTC para comprobaciones intermedias y alertas materiales.
