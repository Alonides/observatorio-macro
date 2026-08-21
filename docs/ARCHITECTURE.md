# Arquitectura v0.2

## Autoridad y gobernanza

1. El ensayo `MEIR-MON-002-A1` fija el significado de H0, H1 y H2.
2. `methodology.yml` fija parámetros, periodos de calibración, fecha de congelación y reglas de adjudicación.
3. El código determinista aplica la especificación; sus resultados no pueden corregirse desde la prosa.
4. Cada salida incorpora versión y hash metodológico. En GitHub Actions incorpora además el commit de código.
5. Los resultados de v0.1 permanecen en `archive/v0.1`; una nueva versión no los recalcula silenciosamente.

## Flujo

`Productores → adaptadores aislados → fusión/revisiones → derivados → calidad`

Desde esa base parten dos ramas que no se agregan:

`→ motor de acontecimiento (92 días) → H0/H1/H2/MIXED/INDETERMINATE`

`→ motor de estado estructural → vector de dimensiones, sin puntuación total`

Ambas se publican en JSON y el visor solo representa esos resultados. Las ventanas de 183 y 365 días son contexto: no pueden activar una hipótesis.

## Motor de acontecimiento

- **H0:** exige prima estadounidense relativa positiva, ausencia de sincronismo global y evidencia que no alcance H1. Nunca se activa por residuo lógico.
- **H1:** exige simultáneamente la alarma triple, especificidad estadounidense y una confirmación independiente.
- **H2:** exige sincronismo global y ausencia de residuo excepcional estadounidense.
- **MIXED:** H2 más las condiciones completas de H1.
- **INDETERMINATE:** evidencia insuficiente o contradictoria.

La triple señal detectó dos episodios de reflación en la calibración disponible —junio de 2009 y febrero de 2011—. Por ello abre investigación y no pretende distinguir por sí sola reflación de pérdida institucional. El contexto de riesgo usa S&P 500, OAS investment-grade y rendimiento corporativo absoluto; el OAS no se interpreta aisladamente porque el Treasury forma parte de su denominador.

La especificidad estadounidense usa provisionalmente una diferencia contra la mediana de Japón, Alemania y Reino Unido. Antes de hacer efectiva v0.2 debe sustituirse por un residuo calibrado, con percentiles p90/p95 y prueba fuera de muestra.

## Motor de estado

Publica por separado:

- nivel y percentil disponible del TIPS real a diez años;
- deuda federal en manos del público/PIB, con deuda bruta como contexto;
- intereses federales/PIB;
- cuota de letras, tenencias oficiales extranjeras y cuota COFER cuando se integren sus fuentes.

No existe `aggregate_score`. Evento y estado responden preguntas distintas: ruptura rápida frente a degradación lenta.

## Datos y fallos

- Cada observación puede contener `period_date`, `published_at`, `retrieved_at`, `value` y `revision`.
- La fecha del periodo no se confunde con la de recogida. `published_at` queda nulo si la fuente no entrega una fecha verificable.
- Una revisión del mismo periodo incrementa `revision`; no se inventa una observación nueva.
- Una fuente rota conserva historial y deja una incidencia explícita; jamás aporta cero.
- La concurrencia está acotada y los paquetes comunes se descargan una sola vez.
- El panel es estático: GitHub Actions escribe JSON y GitHub Pages lo sirve sin backend.

## Capas históricas

La calibración objetivo del motor vivo comienza en 2003, cuando existen TIPS. El histórico retenido todavía es parcial hasta completar el *backfill*. La investigación 1971–2002, que requerirá expectativas de encuesta como proxy, se mantendrá como laboratorio separado y no se mezclará con el clasificador operativo.
