# Observatorio macro

Observatorio macroeconómico automatizado para vigilar el precio del privilegio del dólar, la competencia global por duración y las condiciones de un posible cambio de régimen monetario.

## Qué hace

- Recoge diariamente series de tipos soberanos, inflación implícita, dólar, oro, Bitcoin, energía y liquidez.
- Conserva la fecha de observación y la fecha de recogida: nunca confunde un dato antiguo con uno nuevo.
- Calcula pendientes de la curva estadounidense y cambios a tres meses.
- Clasifica la evidencia entre tres hipótesis no excluyentes:
  - **H0:** reprecio global de la duración.
  - **H1:** pérdida específica de confianza en la promesa fiscal estadounidense.
  - **H2:** combinación de ambas.
- Publica un panel estático que funciona sin servidor.
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

## Automatización

El flujo `.github/workflows/daily.yml` se ejecuta cada día a las 05:30 UTC y también puede iniciarse manualmente desde **Actions → Daily macro ingestion → Run workflow**. Si una fuente falla, conserva los datos válidos, registra el error y marca la carga como parcial.

## Método

El panel es un instrumento de vigilancia, no una recomendación financiera ni un modelo de predicción opaco. Los umbrales están declarados en `src/observatorio/engine.py`; cualquier cambio queda registrado por Git.

Consulta [Arquitectura](docs/ARCHITECTURE.md) y [Diccionario de datos](docs/DATA_DICTIONARY.md).

