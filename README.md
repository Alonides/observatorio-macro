# Observatorio macro

Panel automatizado y auditable para vigilar el precio del privilegio del dólar, la competencia global por duración y la migración entre promesas soberanas y capacidad productiva.

## Qué hace

- Recoge **40 series** y calcula **8 series derivadas**, con productor, transporte, periodo del dato, momento de recogida, revisión y frescura.
- No rellena huecos con cero y conserva el último dato válido cuando una fuente falla.
- Ejecuta dos motores separados:
  - **acontecimiento:** busca cambios de régimen en una ventana primaria de 92 días;
  - **estado estructural:** muestra presiones lentas en sus propias unidades y nunca produce una nota total.
- Añade una capa de numerario oro: bolsa, Bitcoin, divisas y deuda pueden leerse fuera del dólar nominal.
- Publica un panel estático y ejecuta la ingestión diaria en GitHub Actions aunque el ordenador esté apagado.

## Hipótesis canónicas

- **H0 — prima estadounidense de oferta y plazo:** deterioro relativo de la duración estadounidense sin evidencia suficiente de pérdida institucional.
- **H1 — pérdida específica de confianza:** señal triple, especificidad estadounidense y confirmación independiente.
- **H2 — reprecio global de la duración:** subida sincrónica en varios soberanos sin residuo excepcional de EE. UU.
- **MIXED:** choque global con componente estadounidense.
- **INDETERMINATE:** ninguna hipótesis reúne evidencia positiva suficiente.

La ausencia de H1 no demuestra H0. La señal triple —dólar a la baja, TIPS real al alza y breakeven al alza— es una alarma de investigación, no un veredicto. Bolsa, OAS y rendimiento corporativo ayudan a distinguir reflación, estrés sistémico y posible migración hacia capacidad privada, pero una regla simple de «bolsa abajo» no bloquea H1.

La especificidad estadounidense ya no se calcula como una resta simple. Un OLS mensual pre-registrado compara el Treasury a diez años con Japón, Alemania y Reino Unido: 2003–2024 estima los coeficientes y 2025–presente queda fuera de muestra. H0 exige un residuo acumulado de tres meses sobre p90; la especificidad fuerte de H1 exige p95 durante dos cierres consecutivos. El informe completo está en [calibración relativa v0.2](docs/CALIBRATION_REPORT_V02.md).

## Gobernanza metodológica

[`methodology.yml`](methodology.yml) es la fuente única de parámetros, definiciones operativas, periodos de calibración y fechas de congelación. Cada JSON publica su versión y SHA-256 canónico. El ensayo fija la semántica; la especificación y el código determinista fijan el resultado. Si discrepan, el panel declara el conflicto: la prosa no corrige manualmente la salida.

La versión pública v0.1 queda preservada en `archive/v0.1`. La revisión v0.2 se desarrolla en `feature/methodology-v0.2`; no reescribe resultados históricos anteriores.

## Uso local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/collect.py
python -m http.server 8000
```

Después abre `http://localhost:8000`.

Para comprobar conectividad sin modificar los JSON:

```bash
python scripts/source_smoke.py --all
```

La calibración quedó congelada y su artefacto está versionado en `data/calibration/us_relative_v02.json`; el robot diario lo aplica, pero no lo reestima.

```bash
python scripts/verify_calibration.py
```

La verificación es offline: reconstruye el OLS, los residuos y los percentiles desde los cierres mensuales guardados y comprueba la huella fijada en `methodology.yml`.

## Automatización y fuentes

`.github/workflows/daily.yml` se ejecuta cada día a las 05:30 UTC y también desde **Actions → Daily macro ingestion → Run workflow**. Una incidencia aislada produce `operational_partial`; solo la ausencia de una serie nuclear vuelve no operativo el panel.

Se consultan Treasury, Federal Reserve, New York Fed, BLS, EIA, Cboe, LBMA, Norges Bank, ECB, Bundesbank, Bank of England, Ministry of Finance Japan y Fiscal Data. CoinGecko aporta Bitcoin. FRED y DBnomics se usan como transportes declarados cuando la fuente económica o el índice tienen otro productor. El capex emplea *Hyperscaler Capex Tracker* (CC BY 4.0), que conserva la base y las fuentes por fila.

Más detalle: [Arquitectura](docs/ARCHITECTURE.md), [Diccionario de datos](docs/DATA_DICTIONARY.md), [hoja de ruta v0.2](docs/ROADMAP_V02.md) y [registro metodológico](docs/METHODOLOGY_CHANGELOG.md).
