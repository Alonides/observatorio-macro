# Diccionario de datos v0.3

| Bloque | Variables principales | Uso |
|---|---|---|
| Curva EE. UU. | 3m, 2y, 10y, 30y, TIPS 10y, breakeven 10y | Precio fiscal, pendiente y señal triple |
| Liquidez y riesgo | SOFR, IORB, RRP, balance Fed, TGA, VIX | Confirmación de tensión monetaria o de mercado |
| Divisas | dólar amplio, EUR, NOK, JPY, CNY | Denominador y ajuste cambiario |
| Reservas alternativas | oro, Bitcoin | Migración dentro y fuera de la promesa soberana |
| Energía | Brent, Henry Hub | Choque físico e inflación |
| Duración global | Japón, Alemania, Reino Unido, Noruega, eurozona | Diferenciar EE. UU. de un choque mundial |
| Fiscal | deuda federal, intereses, PIB nominal | Capacidad y denominador |
| Economía real | IPC y desempleo | Condiciones de contorno |
| Capacidad productiva | capex FY de Microsoft, Alphabet, Amazon, Meta y Oracle | Competencia privada por capital; no se equipara íntegramente a IA |

`quality` puede ser `ok`, `warning`, `stale` o `missing`. La antigüedad admisible depende de la frecuencia declarada de cada serie.

Cada fila publicada incorpora `source` y `source_url`. `observation_date` es la fecha del dato en origen; `generated_at` es la hora de la ejecución. Las unidades no se homogeneizan silenciosamente: las comparaciones entre activos distintos del panel se muestran como índices base 100.
