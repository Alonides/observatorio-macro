# Arquitectura

## Principios

1. **Fuente y observación separadas.** Cada valor conserva la fecha publicada por la fuente y la fecha de recogida.
2. **Fallo aislado.** Una serie rota no invalida la carga completa; se conserva el último dato y se declara el fallback.
3. **Umbrales versionados.** La lógica H0/H1/H2 vive en código revisable, no en una respuesta generada por IA.
4. **Datos públicos y sin secretos.** El núcleo consulta productores primarios y APIs abiertas sin credenciales privadas.
5. **Robot desacoplado del visor.** GitHub Actions actualiza JSON; el panel solo lo lee.
6. **Historia acumulativa.** Cada descarga se fusiona por fecha con el archivo anterior; una fuente de “último dato” no puede borrar el pasado.

## Flujo

`Productores → adaptadores aislados → fusión histórica → frescura → derivados → motor H0/H1/H2 → JSON → panel`

## Hipótesis

- **H0:** el largo estadounidense sube dentro de un reprecio global de la duración.
- **H1:** aparece simultáneamente dólar débil, rendimiento real alto e inflación implícita alta, confirmado por tensión de liquidez, VIX extremo o deterioro relativo de EE. UU.
- **H2:** concurren el choque mundial y el componente específico estadounidense.

FRED queda fuera del circuito operativo porque su servidor CSV agotó el tiempo desde GitHub Actions. El catálogo actual consulta Norges Bank, ECB, Bundesbank, Bank of England, Ministry of Finance Japan, Treasury, Federal Reserve, New York Fed, BLS, EIA, SEC, Cboe y LBMA; CoinGecko cubre Bitcoin. Las tablas NIPA de BEA se obtienen del espejo DBnomics, declarado como transporte, para no almacenar una clave personal. Un fallo aparece como ausencia o fallback declarado, nunca como cero.

## Próximas capas

- Subastas del Tesoro, bid-to-cover y tails.
- SLR, dealer inventories, fails-to-deliver y basis trade.
- Emisión corporativa de IA y emisión soberana europea por duración.
- Demografía, pasivos contingentes y gasto energético de centros de datos.
- Alerta y resumen diario cuando cambie el régimen o una fuente crítica.
