# Especificación congelada del modelo relativo v0.2

**Registro previo a la estimación:** 22 de agosto de 2026  
**Muestra de calibración:** enero de 2003–diciembre de 2024  
**Fuera de muestra:** enero de 2025–presente  
**Estado al crear este registro:** especificación congelada; coeficientes y umbrales aún no estimados.

Este documento fija las decisiones del modelo antes de consultar sus coeficientes, percentiles o resultados fuera de muestra. Cualquier cambio posterior exige una nueva versión y una entrada explícita en el registro metodológico.

## Pregunta

El modelo no intenta predecir el nivel del Treasury a diez años. Estima qué parte de su variación es común a una cesta de soberanos comparables y calcula el componente específicamente estadounidense. Ese residuo constituye evidencia positiva para H0 o, junto con las demás condiciones del motor, para H1. La ausencia de residuo nunca demuestra H2 por sí sola.

## Series y tratamiento

| Mercado | Serie | Productor | Magnitud |
|---|---|---|---|
| Estados Unidos | `DGS10` | U.S. Treasury | rendimiento par a diez años |
| Japón | `IRLTLT01JPM156N` | Ministerio de Finanzas de Japón | rendimiento soberano a diez años |
| Alemania | `IRLTLT01DEM156N` | Deutsche Bundesbank | rendimiento soberano a diez años |
| Reino Unido | `IRLTLT01GBM156N` | Bank of England | rendimiento soberano a diez años |

Se usan rendimientos en moneda local y sus variaciones en puntos porcentuales. No se convierte a dólares ni se ajusta por cobertura de divisa: el objeto es el choque del tipo de descuento soberano doméstico, no la rentabilidad cubierta de un inversor transfronterizo. Un modelo de rentabilidad cubierta respondería otra pregunta y requerirá otra versión.

Para cada serie se toma la última observación disponible de cada mes natural cerrado. Solo entran meses con las cuatro observaciones; no se imputan huecos, no se estandariza y no se winsoriza.

## Estimación congelada

Sobre primeras diferencias mensuales se estima por mínimos cuadrados ordinarios con intercepto:

`ΔUS_t = α + β_JP·ΔJP_t + β_DE·ΔDE_t + β_UK·ΔUK_t + ε_t`

Los coeficientes se estiman exclusivamente con meses de la muestra 2003–2024. El periodo 2025–presente no puede modificar coeficientes ni umbrales.

El clasificador opera con el residuo acumulado de tres meses:

`S_t = ε_t + ε_(t-1) + ε_(t-2)`

Tres meses son la correspondencia mensual predeclarada de la ventana primaria de 92 días. Las ventanas de dos y cuatro meses se publican solo como sensibilidad: está prohibido escoger a posteriori la que produzca el resultado más intenso.

## Umbrales y adjudicación

Los percentiles se calculan sobre `S_t` dentro de 2003–2024 con el método de rango más próximo: para `n` valores ordenados, `q_p = x_(ceil(p·n))`.

- Evidencia específica para H0: último `S_t ≥ p90`.
- Especificidad fuerte utilizable por H1: `S_t ≥ p95` en dos cierres mensuales consecutivos.
- H1 sigue requiriendo además la alarma triple y una confirmación independiente.
- H2 sigue requiriendo sincronismo global y ausencia de especificidad estadounidense excepcional.
- `MIXED` sigue requiriendo simultáneamente H2 y todas las condiciones de H1.

El modelo solo se actualiza con meses cerrados. Esto introduce un retraso deliberado a cambio de impedir que una observación parcial del mes active o desactive una hipótesis.

## Informe obligatorio

El artefacto de calibración debe publicar, como mínimo:

- fechas exactas, observaciones completas y huellas de las entradas;
- coeficientes, R² y error cuadrático medio;
- p90 y p95 del residuo acumulado a tres meses;
- número y fechas de activación en calibración;
- episodios persistentes por encima de p95;
- resultados fuera de muestra sin reestimación;
- sensibilidad descriptiva a dos y cuatro meses;
- versión y hash de esta metodología.

Si los resultados aconsejan cambiar la cesta, la frecuencia, el tratamiento de moneda, el estimador o el horizonte, no se retoca esta especificación: se abre una v0.3.
