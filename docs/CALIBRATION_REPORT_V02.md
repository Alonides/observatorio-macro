# Informe de calibración relativa v0.2

**Estimación:** 22 de agosto de 2026  
**Especificación previa:** commit remoto `3a03a35d9e89b7047e7c31addf5f78417896c312`  
**Calibración:** 2003-02–2024-12  
**Fuera de muestra:** 2025-01–2026-07  
**Artefacto:** `data/calibration/us_relative_v02.json`  
**SHA-256 del artefacto:** `41acfe0c60eeb73e3a4e7944e54492c32b372f2af26b13d0d2fef5e391a90c36`

## Resultado

El modelo explica el 68,5 % de la variación mensual del Treasury a diez años mediante los movimientos contemporáneos de Japón, Alemania y Reino Unido. No intenta explicar niveles ni atribuir causalidad.

| Parámetro | Estimación |
|---|---:|
| Intercepto mensual | +0,42 pb |
| β Japón | 0,3277 |
| β Alemania | 0,4454 |
| β Reino Unido | 0,5001 |
| R² | 0,6851 |
| RMSE | 14,51 pb |
| Observaciones de estimación | 263 |

Para el residuo acumulado de tres meses, p90 es **+25,55 pb** y p95 es **+35,87 pb**. El primero activa la evidencia relativa de H0; el segundo solo aporta especificidad fuerte a H1 cuando persiste dos cierres consecutivos. H1 continúa necesitando la alarma triple y una confirmación independiente.

## Frecuencia histórica

En la muestra de calibración existen 27 cierres sobre p90 y 14 sobre p95. Seis cierres satisfacen la persistencia p95: diciembre de 2004, enero de 2005, octubre de 2008, abril de 2009, octubre de 2023 y noviembre de 2023.

Estas fechas no se etiquetan retrospectivamente como pérdida de confianza. El residuo solo responde «Estados Unidos se movió mucho más de lo que predijo la cesta». Puede recoger oferta fiscal, política monetaria relativa, liquidez u otros factores. La adjudicación H1 pertenece al motor conjunto.

## Prueba fuera de muestra

Entre enero de 2025 y julio de 2026 el clasificador de tres meses no cruza p90 ni p95. Los últimos valores son:

| Cierre | Residuo 3m |
|---|---:|
| febrero de 2026 | −7,90 pb |
| marzo de 2026 | −26,86 pb |
| abril de 2026 | −29,93 pb |
| mayo de 2026 | −6,17 pb |
| junio de 2026 | +16,57 pb |
| julio de 2026 | +19,07 pb |

Por tanto, al corte actual no hay evidencia relativa suficiente para H0 ni especificidad fuerte para H1. Si el sincronismo global cumple su regla, el modelo es compatible con H2. Esto es una salida calculada, no una corrección narrativa del ensayo.

## Sensibilidad predeclarada

| Horizonte | p90 | p95 | Activaciones p90 fuera de muestra | Activaciones p95 fuera de muestra |
|---|---:|---:|---:|---:|
| 2 meses | +24,69 pb | +29,71 pb | 1 (mayo de 2025) | 0 |
| **3 meses operativo** | **+25,55 pb** | **+35,87 pb** | **0** | **0** |
| 4 meses | +31,91 pb | +40,92 pb | 0 | 0 |

La diferencia de dos meses no autoriza a cambiar de ventana: seleccionar el máximo entre horizontes convertiría la sensibilidad en búsqueda retrospectiva. Cualquier cambio del horizonte operativo exige una nueva versión.

## Procedencia y límites

- Estados Unidos: archivos diarios del U.S. Treasury.
- Japón: histórico y mes corriente del Ministerio de Finanzas.
- Alemania: serie soberana a diez años de Deutsche Bundesbank.
- Reino Unido: `IUDMNPY` del Bank of England.
- Se usan cierres mensuales y variaciones de rendimientos en moneda local, sin imputación.

El modelo no incorpora cobertura de divisa, no prueba estabilidad estructural eterna y actualiza la clasificación solo tras cerrar el mes. Esas limitaciones son visibles y deliberadas. Reestimar, cambiar cesta o añadir cobertura exige una versión nueva; el robot diario solo aplica estos parámetros.
