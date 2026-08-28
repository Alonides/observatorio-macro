# Informe Debt/NOK · 2026-08-28

**Estado oficial: Normal.** Sin configuración activa de crisis; vigilancia estructural normal

El detector no identifica actualmente una configuración de crisis de deuda/dólar ni estrés material de NOK.

**Actualizado en Oslo:** 2026-08-28 21:06. **Último dato oficial disponible:** 2026-08-27. **Bloque oficial más retrasado:** URP (4 días hábiles).

## Frescura oficial de los bloques

| Bloque | Datos a | Retraso aproximado | Estado |
|---|---|---:|---|
| URP | 2026-08-21 | 4 días hábiles | Obsoleto |
| URR | 2026-08-21 | 4 días hábiles | Obsoleto |
| DSS | 2026-08-21 | 4 días hábiles | Obsoleto |
| NKS | 2026-08-21 | 4 días hábiles | Obsoleto |
| NRS | 2026-08-21 | 4 días hábiles | Obsoleto |

## Panel oficial de bloques

| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |
|---|---:|---|---|---:|---:|
| URP · Rechazo USA | 0.00 | inactive | 2026-08-21 | 0.00 | +0.00 |
| URR · Persistencia USA | 0.00 | inactive | 2026-08-21 | 0.00 | +0.00 |
| DSS · Escasez de dólares | 0.00 | inactive | 2026-08-21 | 0.00 | +0.00 |
| NKS · Estrés NOK | 0.00 | normal | 2026-08-21 | 0.00 | +0.00 |
| NRS · Reversión NOK | 0.00 | inactive | 2026-08-21 | 0.00 | +0.00 |

## Variables discriminantes oficiales

- Treasury 30 años, cambio 10 sesiones: **8.0 pb**.
- Dólar amplio, caída 10 sesiones: **0.84 %**.
- VIX: **15.13**.
- EUR/NOK, cambio 20 sesiones: **-0.39 %**.
- Debilidad NOK frente a SEK, 20 sesiones: **-0.51 %**.
- Residual NOK: **-0.39σ**.
- Norway–Bund, cambio 20 sesiones: **-13.2 pb**.

## Lectura operativa oficial

- Ningún bloque operativo supera sus umbrales de vigilancia.

## Lectura rápida provisional

**Normal.** La vía rápida provisional no eleva el nivel de la lectura oficial.

La vía rápida usa proxies primarios o secundarios expresamente identificados y validados. No confirma por sí sola un cambio de régimen; la lectura oficial conserva prioridad.

| Bloque | Oficial | Provisional | Δ | Estado provisional | Datos provisionales a |
|---|---:|---:|---:|---|---|
| URP | 0.00 | 0.00 | 0.00 | inactive | 2026-08-21 |
| URR | 0.00 | 0.00 | 0.00 | inactive | 2026-08-21 |
| DSS | 0.00 | 0.00 | 0.00 | inactive | 2026-08-21 |
| NKS | 0.00 | 0.00 | 0.00 | normal | 2026-08-27 |
| NRS | 0.00 | 0.00 | 0.00 | inactive | 2026-08-27 |

### Puentes de datos

| Serie | Estado | Oficial hasta | Proxy hasta | Extensión hasta | Correlación | Error medio |
|---|---|---|---|---|---:|---:|
| DEXUSEU | active | 2026-08-21 | 2026-08-28 | 2026-08-28 | 0.614 | 0.225 pp |
| DEXNOUS | active | 2026-08-21 | 2026-08-28 | 2026-08-28 | 0.710 | 0.298 pp |
| DEXSDUS | active | 2026-08-21 | 2026-08-28 | 2026-08-28 | 0.655 | 0.391 pp |
| DTWEXBGS | expired | 2026-08-21 | 2026-08-28 | — | 0.609 | 0.192 pp |
| DCOILBRENTEU | active | 2026-08-25 | 2026-08-28 | 2026-08-28 | 0.861 | 1.643 pp |

**Fuentes rápidas no disponibles:**
- CME_WTI_SETTLEMENT: CME WTI settlements unavailable: 2026-08-10: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT?tradeDate=08%2F10%2F2026: HTTP Error 403: Forbidden

## Método y límites

El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque oficial usa su propia fecha completa de datos; los datos ausentes no se imputan como cero.

La vía rápida provisional utiliza únicamente rendimientos de proxies primarios o secundarios expresamente identificados y validados, reanclados al último nivel oficial. No sobrescribe historia, caduca automáticamente y nunca sustituye la lectura oficial.

La frescura no altera scores, pesos ni umbrales. Una señal provisional divergente solicita revisión humana; sólo la publicación oficial puede confirmarla dentro del modelo operativo.

Cadencia: Lunes, 07:30 UTC para el informe completo; Martes a viernes, 07:00 UTC para comprobaciones intermedias y alertas materiales.
