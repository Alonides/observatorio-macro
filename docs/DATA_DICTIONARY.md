# Diccionario de datos v0.2

## Capas

| Bloque | Variables principales | Uso |
|---|---|---|
| Curva EE. UU. | 3m, 2y, 10y, 30y, TIPS 10y, breakeven 10y | Precio fiscal, pendientes y alarma triple |
| Liquidez | SOFR, IORB, RRP, balance Fed, TGA | Confirmación monetaria y microestructura |
| Riesgo y crédito | VIX, S&P 500, OAS IG, rendimiento efectivo IG | Separar reflación, estrés y migración privada |
| Divisas | dólar amplio, EUR, NOK, JPY, CNY | Denominador y ajuste cambiario |
| Reserva y numerario | oro, Bitcoin y ocho cocientes en oro | Comparar valor real fuera del dólar nominal |
| Energía | Brent, Henry Hub | Choque físico e inflación |
| Duración global | EE. UU., Japón, Alemania, Reino Unido, Noruega, euro AAA | Diferenciar un residuo de EE. UU. de un choque mundial |
| Fiscal | deuda bruta, deuda en manos del público, intereses, PIB | Capacidad, carga y denominador |
| Economía real | IPC y desempleo | Condiciones de contorno |
| Capacidad productiva | capex de Microsoft, Alphabet, Amazon, Meta y Oracle | Competencia física por recursos y capital |

El catálogo contiene 40 series recogidas y 8 derivadas. La suma del capex es descriptiva: la base contable varía según la guía de cada compañía y no equivale íntegramente a IA. La competencia financiera por el mismo libro de duración —emisión corporativa larga y soberana europea— sigue pendiente de una fuente diaria o mensual reproducible.

## Artefacto del modelo relativo

`data/calibration/us_relative_v02.json` conserva 283 cierres mensuales completos de Estados Unidos, Japón, Alemania y Reino Unido, sus fechas de observación, la huella SHA-256 de los insumos, coeficientes, umbrales, activaciones y resultados fuera de muestra. No es una serie adicional del panel ni se reestima a diario. `methodology.yml` fija su propia huella SHA-256 para impedir que un artefacto distinto se cargue bajo el mismo nombre.

Los rendimientos se comparan en moneda local porque el objeto es el cambio del tipo de descuento soberano doméstico. No representan la rentabilidad cubierta en dólares de un inversor internacional.

## Derivados en oro

| ID | Fórmula | Unidad |
|---|---|---|
| `SP500_XAU` | S&P 500 / oro USD | ratio |
| `BTC_XAU` | Bitcoin USD / oro USD | onzas/BTC |
| `XAU_NOK` | oro USD × NOK/USD | NOK/onza |
| `XAU_EUR` | oro USD / USD/EUR | EUR/onza |
| `XAU_JPY` | oro USD × JPY/USD | JPY/onza |
| `XAU_CNY` | oro USD × CNY/USD | CNY/onza |
| `US_PUBLIC_DEBT_XAU` | deuda en manos del público / oro USD | millones de onzas |
| `US_GROSS_DEBT_XAU` | deuda federal bruta / oro USD | millones de onzas |

La alineación es *as-of*: usa el último denominador conocido con un máximo de siete días y nunca mira hacia el futuro. Los rendimientos no se dividen por oro; para comparar bonos en oro se necesitará una serie de precio o retorno total.

## Semántica temporal

| Campo | Significado |
|---|---|
| `period_date` | periodo o fecha efectiva a la que pertenece el dato |
| `observation_date` | alias transitorio de `period_date` para compatibilidad con v0.1 |
| `published_at` | fecha de publicación si la fuente la entrega de forma verificable |
| `retrieved_at` | primera recogida del valor actual; cambia si existe revisión |
| `revision` | número de cambios observados para ese periodo |
| `generated_at` | momento de construcción del archivo completo |

`quality` puede ser `ok`, `warning`, `stale` o `missing`. Los límites son específicos por frecuencia: 65 días para series mensuales y 160 para trimestrales en v0.2. Un valor pendiente no se sustituye por cero.

## Magnitudes fiscales

`US_PUBLIC_DEBT_GDP` usa deuda en manos del público y es la medida principal de presión de financiación. `US_GROSS_DEBT_GDP` se publica como contexto. No deben describirse como la misma cifra.

## Procedencia

Cada fila contiene `source` y `source_url`; cuando existe un transporte intermedio se nombra explícitamente. `methodology` contiene la versión y el SHA-256 de la especificación. `code_commit` se rellena en GitHub Actions.
