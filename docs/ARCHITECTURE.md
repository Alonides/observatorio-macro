# Arquitectura

## Principios

1. **Fuente y observación separadas.** Cada valor conserva la fecha publicada por la fuente y la fecha de recogida.
2. **Fallo aislado.** Una serie rota no invalida la carga completa; se conserva el último dato y se declara el fallback.
3. **Umbrales versionados.** La lógica H0/H1/H2 vive en código revisable, no en una respuesta generada por IA.
4. **Datos públicos y sin secretos en v0.1.** El recolector inicial usa CSV público de FRED y no requiere API keys.
5. **Robot desacoplado del visor.** GitHub Actions actualiza JSON; el panel solo lo lee.

## Flujo

`Fuentes → fetch/parse → validación de frescura → serie histórica → derivados → motor de régimen → latest.json → panel`

## Hipótesis

- **H0:** el largo estadounidense sube dentro de un reprecio global de la duración.
- **H1:** aparece simultáneamente dólar débil, rendimiento real alto e inflación implícita alta, confirmado por tensión de liquidez o deterioro relativo de EE. UU.
- **H2:** concurren el choque mundial y el componente específico estadounidense.

Las series soberanas internacionales iniciales son mensuales y funcionan como primera cesta comparativa. La siguiente versión añadirá fuentes oficiales diarias de Norges Bank, ECB, Bank of England, Ministry of Finance Japan y Treasury Fiscal Data.

## Próximas capas

- Subastas del Tesoro, bid-to-cover y tails.
- SLR, dealer inventories, fails-to-deliver y basis trade.
- Emisión corporativa de IA y emisión soberana europea por duración.
- Demografía, pasivos contingentes y gasto energético de centros de datos.
- Publicación autenticada del panel y resúmenes diarios en ChatGPT.

