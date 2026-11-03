# Informe Debt/NOK · 2026-11-03

**Estado oficial: Normal.** Sin configuración activa de crisis; vigilancia estructural normal

El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK.

**Actualizado en Oslo:** 2026-11-03 15:41. **Último dato oficial disponible:** 2026-11-02. **Bloque oficial más retrasado:** URR (25 días hábiles).

## Frescura oficial de los bloques

| Bloque | Datos a | Retraso aproximado | Estado |
|---|---|---:|---|
| URP | 2026-10-23 | 6 días hábiles | Obsoleto |
| URR | 2026-09-28 | 25 días hábiles | Obsoleto |
| DSS | 2026-10-23 | 6 días hábiles | Obsoleto |
| NKS | 2026-10-27 | 4 días hábiles | Obsoleto |
| NRS | 2026-10-27 | 4 días hábiles | Obsoleto |

## Panel oficial de bloques

| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |
|---|---:|---|---|---:|---:|
| URP · Rechazo USA | 0.00 | inactive | 2026-10-23 | 0.00 | +0.00 |
| URR · Persistencia USA | 0.00 | inactive | 2026-09-28 | 0.00 | +0.00 |
| DSS · Escasez de dólares | 0.00 | inactive | 2026-10-23 | 0.00 | +0.00 |
| NKS · Estrés NOK | 5.10 | normal | 2026-10-27 | 3.74 | +1.36 |
| NRS · Reversión NOK | 0.00 | inactive | 2026-10-27 | 0.00 | +0.00 |

## Variables discriminantes oficiales

- Treasury 30 años, cambio 10 sesiones: **-27.0 pb**.
- Dólar amplio, caída 10 sesiones: **0.10 %**.
- VIX: **19.45**.
- EUR/NOK, cambio 20 sesiones: **-3.98 %**.
- Debilidad NOK frente a SEK, 20 sesiones: **-1.79 %**.
- Residual NOK: **-1.70σ**.
- Norway–Bund, cambio 20 sesiones: **11.6 pb**.

## Lectura operativa oficial

- Ningún bloque operativo supera sus umbrales de vigilancia.

## Lectura rápida provisional

**Normal.** La vía rápida provisional no eleva el nivel de la lectura oficial.

La vía rápida usa proxies primarios o secundarios expresamente identificados y validados. No confirma por sí sola un cambio de régimen; la lectura oficial conserva prioridad.

| Bloque | Oficial | Provisional | Δ | Estado provisional | Datos provisionales a |
|---|---:|---:|---:|---|---|
| URP | 0.00 | 0.00 | 0.00 | inactive | 2026-10-23 |
| URR | 0.00 | 0.00 | 0.00 | inactive | 2026-09-28 |
| DSS | 0.00 | 0.00 | 0.00 | inactive | 2026-10-23 |
| NKS | 5.10 | 0.00 | -5.10 | normal | 2026-10-30 |
| NRS | 0.00 | 0.00 | 0.00 | inactive | 2026-10-30 |

### Puentes de datos

| Serie | Estado | Oficial hasta | Proxy hasta | Extensión hasta | Correlación | Error medio |
|---|---|---|---|---|---:|---:|
| DEXUSEU | rejected | 2026-10-30 | 2026-11-02 | — | 0.563 | 0.198 pp |
| DEXNOUS | rejected | 2026-10-30 | 2026-11-02 | — | 0.619 | 0.223 pp |
| DEXSDUS | rejected | 2026-10-30 | 2026-11-02 | — | 0.559 | 0.284 pp |
| DTWEXBGS | expired | 2026-10-23 | 2026-11-02 | — | 0.568 | 0.180 pp |
| DCOILBRENTEU | active | 2026-10-27 | 2026-11-02 | 2026-11-02 | 0.654 | 1.874 pp |

**Fuentes rápidas no disponibles:**
- CME_WTI_SETTLEMENT: CME WTI settlements unavailable: 2026-10-16: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT?tradeDate=10%2F16%2F2026: HTTP Error 403: Forbidden

## Método y límites

El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque oficial usa su propia fecha completa de datos; los datos ausentes no se imputan como cero.

La vía rápida provisional utiliza únicamente rendimientos de proxies primarios o secundarios expresamente identificados y validados, reanclados al último nivel oficial. No sobrescribe historia, caduca automáticamente y nunca sustituye la lectura oficial.

La frescura no altera scores, pesos ni umbrales. Una señal provisional divergente solicita revisión humana; sólo la publicación oficial puede confirmarla dentro del modelo operativo.

Cadencia: Lunes, 07:30 UTC para el informe completo; Martes a viernes, 07:00 UTC para comprobaciones intermedias y alertas materiales.
