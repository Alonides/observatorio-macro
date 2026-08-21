# Observatorio macro

Observatorio macroeconómico automatizado para vigilar el precio del privilegio del dólar, la competencia global por duración y las condiciones de un posible cambio de régimen monetario.

## Qué hace

- Recoge 36 series: fuentes oficiales para macro y mercados, más un dataset especializado de capex con metodología, licencia y fuentes por fila.
- Conserva la fecha de observación y la fecha de recogida: nunca confunde un dato antiguo con uno nuevo.
- Calcula pendientes de la curva estadounidense y cambios a tres meses.
- Clasifica la evidencia entre tres hipótesis no excluyentes:
  - **H0:** reprecio global de la duración.
  - **H1:** pérdida específica de confianza en la promesa fiscal estadounidense.
  - **H2:** combinación de ambas.
- Publica un panel estático, móvil y sin servidor con histórico, foco noruego, trazabilidad y gráficos comparables.
- Ejecuta pruebas y una recogida diaria mediante GitHub Actions, aunque el ordenador esté apagado.

## Uso local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/collect.py
python -m http.server 8000
```

Después abre `http://localhost:8000`.

Para comprobar solo conectividad sin modificar los JSON:

```bash
python scripts/source_smoke.py --all
```

## Automatización

El flujo `.github/workflows/daily.yml` se ejecuta cada día a las 05:30 UTC y también puede iniciarse manualmente desde **Actions → Daily macro ingestion → Run workflow**. Si una fuente falla, conserva los datos válidos, registra el error y marca la carga como parcial.

El histórico se fusiona por fecha: las fuentes que solo publican el último nivel (por ejemplo H.4.1) amplían la serie en cada ejecución en vez de borrar observaciones previas.

## Método

El panel es un instrumento de vigilancia, no una recomendación financiera ni un modelo de predicción opaco. Los umbrales están declarados en `src/observatorio/engine.py`; cualquier cambio queda registrado por Git.

El circuito operativo no depende de FRED. Consulta Treasury, Federal Reserve, New York Fed, BLS, EIA, Cboe, LBMA, Norges Bank, ECB, Bundesbank, Bank of England y Ministry of Finance Japan; CoinGecko aporta Bitcoin. Las dos tablas NIPA de BEA viajan por el espejo abierto DBnomics porque la API directa exige una clave personal. La SEC bloquea de forma persistente los rangos de GitHub Actions; por eso el bloque empresarial usa el *Hyperscaler Capex Tracker* (CC BY 4.0), que conserva base, método y fuentes de cada fila. El panel declara siempre el transporte real.

Consulta [Arquitectura](docs/ARCHITECTURE.md) y [Diccionario de datos](docs/DATA_DICTIONARY.md).
