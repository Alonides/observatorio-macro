# Informe Debt/NOK · 2026-09-30

**Estado oficial: Normal.** Sin configuración activa de crisis; vigilancia estructural normal

El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK.

**Actualizado en Oslo:** 2026-09-30 15:05. **Último dato oficial disponible:** 2026-09-29. **Bloque oficial más retrasado:** NKS (5 días hábiles).

## Frescura oficial de los bloques

| Bloque | Datos a | Retraso aproximado | Estado |
|---|---|---:|---|
| URP | 2026-09-25 | 2 días hábiles | Retrasado |
| URR | 2026-09-25 | 2 días hábiles | Retrasado |
| DSS | 2026-09-25 | 2 días hábiles | Retrasado |
| NKS | 2026-09-22 | 5 días hábiles | Obsoleto |
| NRS | 2026-09-22 | 5 días hábiles | Obsoleto |

## Panel oficial de bloques

| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |
|---|---:|---|---|---:|---:|
| URP · Rechazo USA | 0.00 | inactive | 2026-09-25 | 0.00 | +0.00 |
| URR · Persistencia USA | 0.00 | inactive | 2026-09-25 | 0.00 | +0.00 |
| DSS · Escasez de dólares | 0.00 | inactive | 2026-09-25 | 0.00 | +0.00 |
| NKS · Estrés NOK | 0.00 | normal | 2026-09-22 | 0.00 | +0.00 |
| NRS · Reversión NOK | 0.00 | inactive | 2026-09-22 | 0.00 | +0.00 |

## Variables discriminantes oficiales

- Treasury 30 años, cambio 10 sesiones: **14.0 pb**.
- Dólar amplio, caída 10 sesiones: **-1.79 %**.
- VIX: **14.87**.
- EUR/NOK, cambio 20 sesiones: **-0.42 %**.
- Debilidad NOK frente a SEK, 20 sesiones: **-2.25 %**.
- Residual NOK: **-0.35σ**.
- Norway–Bund, cambio 20 sesiones: **-9.5 pb**.

## Lectura operativa oficial

- Ningún bloque operativo supera sus umbrales de vigilancia.

## Lectura rápida provisional

**Normal.** La vía rápida provisional no eleva el nivel de la lectura oficial.

La vía rápida usa proxies primarios o secundarios expresamente identificados y validados. No confirma por sí sola un cambio de régimen; la lectura oficial conserva prioridad.

| Bloque | Oficial | Provisional | Δ | Estado provisional | Datos provisionales a |
|---|---:|---:|---:|---|---|
| URP | 0.00 | 0.00 | 0.00 | inactive | 2026-09-29 |
| URR | 0.00 | 0.00 | 0.00 | inactive | 2026-09-28 |
| DSS | 0.00 | 0.00 | 0.00 | inactive | 2026-09-29 |
| NKS | 0.00 | 3.07 | 3.07 | normal | 2026-09-25 |
| NRS | 0.00 | 0.00 | 0.00 | inactive | 2026-09-25 |

### Puentes de datos

| Serie | Estado | Oficial hasta | Proxy hasta | Extensión hasta | Correlación | Error medio |
|---|---|---|---|---|---:|---:|
| DEXUSEU | active | 2026-09-25 | 2026-09-29 | 2026-09-29 | 0.608 | 0.190 pp |
| DEXNOUS | active | 2026-09-25 | 2026-09-29 | 2026-09-29 | 0.741 | 0.215 pp |
| DEXSDUS | rejected | 2026-09-25 | 2026-09-29 | — | 0.568 | 0.342 pp |
| DTWEXBGS | active | 2026-09-25 | 2026-09-29 | 2026-09-29 | 0.619 | 0.175 pp |
| DCOILBRENTEU | active | 2026-09-22 | 2026-09-29 | 2026-09-29 | 0.889 | 1.445 pp |

**Fuentes rápidas no disponibles:**
- CME_WTI_SETTLEMENT: CME WTI settlements unavailable: 2026-09-14: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT?tradeDate=09%2F14%2F2026: HTTP Error 403: Forbidden

## Método y límites

El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque oficial usa su propia fecha completa de datos; los datos ausentes no se imputan como cero.

La vía rápida provisional utiliza únicamente rendimientos de proxies primarios o secundarios expresamente identificados y validados, reanclados al último nivel oficial. No sobrescribe historia, caduca automáticamente y nunca sustituye la lectura oficial.

La frescura no altera scores, pesos ni umbrales. Una señal provisional divergente solicita revisión humana; sólo la publicación oficial puede confirmarla dentro del modelo operativo.

Cadencia: Lunes, 07:30 UTC para el informe completo; Martes a viernes, 07:00 UTC para comprobaciones intermedias y alertas materiales.
