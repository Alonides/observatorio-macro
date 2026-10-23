# Informe Debt/NOK · 2026-10-23

**Estado oficial: Normal.** Sin configuración activa de crisis; vigilancia estructural normal

El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK.

**Actualizado en Oslo:** 2026-10-23 14:13. **Último dato oficial disponible:** 2026-10-22. **Bloque oficial más retrasado:** URR (18 días hábiles).

## Frescura oficial de los bloques

| Bloque | Datos a | Retraso aproximado | Estado |
|---|---|---:|---|
| URP | 2026-10-16 | 4 días hábiles | Obsoleto |
| URR | 2026-09-28 | 18 días hábiles | Obsoleto |
| DSS | 2026-10-16 | 4 días hábiles | Obsoleto |
| NKS | 2026-10-16 | 4 días hábiles | Obsoleto |
| NRS | 2026-10-16 | 4 días hábiles | Obsoleto |

## Panel oficial de bloques

| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |
|---|---:|---|---|---:|---:|
| URP · Rechazo USA | 0.00 | inactive | 2026-10-16 | 0.00 | +0.00 |
| URR · Persistencia USA | 0.00 | inactive | 2026-09-28 | 0.00 | +0.00 |
| DSS · Escasez de dólares | 0.00 | inactive | 2026-10-16 | 0.00 | +0.00 |
| NKS · Estrés NOK | 6.25 | normal | 2026-10-16 | 4.90 | +1.35 |
| NRS · Reversión NOK | 0.00 | inactive | 2026-10-16 | 0.00 | +0.00 |

## Variables discriminantes oficiales

- Treasury 30 años, cambio 10 sesiones: **-18.0 pb**.
- Dólar amplio, caída 10 sesiones: **0.31 %**.
- VIX: **19.99**.
- EUR/NOK, cambio 20 sesiones: **-1.91 %**.
- Debilidad NOK frente a SEK, 20 sesiones: **-0.74 %**.
- Residual NOK: **-0.90σ**.
- Norway–Bund, cambio 20 sesiones: **14.2 pb**.

## Lectura operativa oficial

- Ningún bloque operativo supera sus umbrales de vigilancia.

## Lectura rápida provisional

**Normal.** La vía rápida provisional no eleva el nivel de la lectura oficial.

La vía rápida usa proxies primarios o secundarios expresamente identificados y validados. No confirma por sí sola un cambio de régimen; la lectura oficial conserva prioridad.

| Bloque | Oficial | Provisional | Δ | Estado provisional | Datos provisionales a |
|---|---:|---:|---:|---|---|
| URP | 0.00 | 0.00 | 0.00 | inactive | 2026-10-22 |
| URR | 0.00 | 0.00 | 0.00 | inactive | 2026-09-28 |
| DSS | 0.00 | 0.00 | 0.00 | inactive | 2026-10-22 |
| NKS | 6.25 | 6.25 | 0.00 | normal | 2026-10-16 |
| NRS | 0.00 | 0.00 | 0.00 | inactive | 2026-10-16 |

### Puentes de datos

| Serie | Estado | Oficial hasta | Proxy hasta | Extensión hasta | Correlación | Error medio |
|---|---|---|---|---|---:|---:|
| DEXUSEU | active | 2026-10-16 | 2026-10-22 | 2026-10-22 | 0.618 | 0.215 pp |
| DEXNOUS | active | 2026-10-16 | 2026-10-22 | 2026-10-22 | 0.679 | 0.225 pp |
| DEXSDUS | rejected | 2026-10-16 | 2026-10-22 | — | 0.589 | 0.328 pp |
| DTWEXBGS | active | 2026-10-16 | 2026-10-22 | 2026-10-22 | 0.608 | 0.195 pp |
| DCOILBRENTEU | active | 2026-10-20 | 2026-10-22 | 2026-10-22 | 0.701 | 1.882 pp |

**Fuentes rápidas no disponibles:**
- CME_WTI_SETTLEMENT: CME WTI settlements unavailable: 2026-10-05: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT?tradeDate=10%2F05%2F2026: HTTP Error 403: Forbidden

## Método y límites

El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque oficial usa su propia fecha completa de datos; los datos ausentes no se imputan como cero.

La vía rápida provisional utiliza únicamente rendimientos de proxies primarios o secundarios expresamente identificados y validados, reanclados al último nivel oficial. No sobrescribe historia, caduca automáticamente y nunca sustituye la lectura oficial.

La frescura no altera scores, pesos ni umbrales. Una señal provisional divergente solicita revisión humana; sólo la publicación oficial puede confirmarla dentro del modelo operativo.

Cadencia: Lunes, 07:30 UTC para el informe completo; Martes a viernes, 07:00 UTC para comprobaciones intermedias y alertas materiales.
