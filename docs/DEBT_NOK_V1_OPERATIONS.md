# Debt/NOK Monitor v1.0.3 · operación

## Qué queda congelado

La versión operativa v1.0.3 no altera las ecuaciones validadas del núcleo v0.4.1. Mantiene:

- estados oficiales `normal`, `watch`, `alert` y `critical`;
- separación explícita entre `gate_score` y `operational_score` en NRS;
- fechas y frescura propias para URP, URR, DSS, NKS y NRS;
- informe determinista en español;
- panel web específico;
- agente programado con trazabilidad en Git;
- entrega por notificaciones de GitHub, sin credenciales de correo almacenadas.

La corrección v1.0.1 distinguió una **reversión NOK confirmada** de un deterioro crítico: NRS genera una alerta material de cambio de régimen, pero no convierte por sí solo el panel en rojo. También impide interpretar periodos sin historia Norway–Bund como resultados negativos de NRS.

La mejora v1.0.2 separó la **fecha del informe** de la **fecha de los datos** y evitó que la fuente más lenta retrasase silenciosamente todos los bloques.

La mejora v1.0.3 añade una **vía rápida provisional** separada. Su finalidad es detectar antes una posible configuración material cuando H.10 o Brent spot se publican con retraso. No cambia, sustituye ni reescribe la lectura oficial.

## Dos carriles

### Carril oficial y autoritativo

Usa las series oficiales congeladas del modelo. Sus scores, estados y alertas son los únicos que pueden confirmar una configuración operativa.

### Carril provisional

Usa rendimientos de proxies oficiales para prolongar, durante pocos días, una serie lenta. Cada rendimiento se aplica al último nivel oficial disponible. El carril provisional:

- se identifica siempre como provisional;
- nunca sobrescribe observaciones oficiales;
- no se guarda en `data/debt_nok/history.json`;
- caduca si el nivel oficial lleva demasiado tiempo sin actualizarse;
- se desactiva si el proxy no supera las pruebas de seguimiento;
- puede solicitar revisión humana, pero no confirma por sí solo un régimen.

Un resultado provisional `critical` se presenta como **alerta provisional máxima**, nunca como estado crítico oficial.

## Proxies oficiales

### Divisas y dólar

Los tipos de referencia del Banco Central Europeo se utilizan para prolongar provisionalmente:

- `DEXUSEU`: USD por EUR;
- `DEXNOUS`: NOK por USD;
- `DEXSDUS`: SEK por USD.

Con las mismas referencias del BCE se construye una cesta relativa de seis divisas —EUR, JPY, GBP, CAD, SEK y CHF— para prolongar provisionalmente `DTWEXBGS`. La cesta no pretende reproducir el nivel del índice amplio de la Reserva Federal: sólo aporta rendimientos recientes, que se reanclan al último nivel oficial.

### Petróleo

El futuro WTI contrato 1 de la U.S. Energy Information Administration se utiliza para prolongar provisionalmente Brent spot. Se emplea sólo cuando su relación reciente con Brent supera los umbrales declarados.

## Validación de cada puente

Antes de activar una extensión se comprueban:

- número mínimo de retornos solapados;
- correlación mínima;
- error absoluto medio máximo entre retornos;
- proximidad temporal del ancla común;
- antigüedad máxima del último nivel oficial;
- movimiento acumulado máximo de la extensión.

Los umbrales están versionados en `src/observatorio/debt_nok_v1/fast_bridge.py`. Si una comprobación falla, el puente queda `rejected`; si el dato oficial es demasiado antiguo, queda `expired`.

## Fechas y frescura por bloque

Cada bloque oficial se evalúa en su última fecha completa propia:

- **URP:** Treasury 30 años, dólar amplio, riesgo y prima relativa USA–Bund.
- **URR:** fecha URP más oro y rendimiento real cuando están disponibles.
- **DSS:** Treasury 30 años, dólar amplio y riesgo.
- **NKS:** EUR/NOK, NOK/SEK, residual NOK y funding disponible.
- **NRS:** EUR/NOK, NOK/SEK, Norway–Bund y Brent; el residual sigue siendo obligatorio para confirmar una reversión.

El informe muestra para cada bloque:

- `asof`: fecha exacta de la lectura;
- `business_day_lag`: días hábiles aproximados frente al dato de mercado más reciente;
- estado de frescura: `fresh`, `delayed`, `stale` o `unavailable`;
- fechas de sus inputs.

Los estados de frescura se interpretan así:

- **Actualizado:** retraso de cero o un día hábil;
- **Retrasado:** dos o tres días hábiles;
- **Obsoleto:** más de tres días hábiles;
- **No disponible:** falta una entrada obligatoria.

La fecha que encabeza el informe es la fecha de generación en `Europe/Oslo`. Las fechas oficiales y provisionales se presentan por separado.

## Comparación a cinco sesiones

El cambio oficial frente a hace cinco sesiones se calcula por bloque:

- URP, URR y DSS retroceden cinco observaciones de Treasury 30 años desde su propia fecha;
- NKS y NRS retroceden cinco observaciones de EUR/NOK desde su propia fecha.

La vía rápida muestra además la diferencia entre el score oficial y el provisional para cada bloque.

## Notificaciones

La notificación diaria se activa cuando:

- aparece una alerta oficial nueva; o
- una vía provisional válida es más severa que la oficial y alcanza nivel de alerta.

La segunda situación genera el título **Señal provisional** y exige revisión humana. El `fingerprint` incluye estados oficiales, estados provisionales y fechas de los puentes para evitar notificaciones repetidas.

## Cadencia elegida

- **Lunes 07:30 UTC:** informe completo semanal. Equivale aproximadamente a 08:30 en Oslo durante el horario de invierno y 09:30 durante el horario de verano.
- **Martes a viernes 07:00 UTC:** comprobación intermedia. Sólo crea una notificación nueva cuando aparece una alerta material distinta de la ya registrada.
- **Cambios del código operativo en `main`:** ejecutan un informe completo inicial o de verificación.

El recolector macro general continúa funcionando diariamente a las 05:30 UTC. El agente Debt/NOK se ejecuta después y utiliza el snapshot más reciente disponible.

## Entrega

El informe se publica siempre en:

- `debt-nok.html`;
- `data/debt_nok/latest.json`;
- `data/debt_nok/latest.md`;
- `data/debt_nok/reports/YYYY-MM-DD.md` para informes semanales y alertas.

El nombre del informe histórico usa la fecha de generación en Oslo, no la fecha del bloque más lento.

El informe semanal se añade como comentario a un único issue titulado **Debt/NOK · informes periódicos**, asignado a `Alonides`. GitHub normalmente envía una notificación por correo al usuario asignado. Las alertas oficiales y las divergencias provisionales materiales se abren como incidencias independientes.

No se usan secretos SMTP ni claves de un proveedor de correo.

## Niveles oficiales

### Normal

Ningún bloque supera el umbral de vigilancia.

### Vigilancia

Se activa por cualquiera de los siguientes:

- URR registra un pulso no persistente;
- URP ≥ 40;
- DSS ≥ 50;
- NKS ≥ 35.

### Alerta

Se activa por cualquiera de los siguientes:

- URR detecta discriminación estadounidense;
- URP ≥ 60;
- DSS ≥ 70;
- NKS ≥ 65;
- NRS confirma una reversión NOK posterior a un shock.

### Crítico

Se activa por cualquiera de los siguientes:

- URR confirma régimen persistente de rechazo;
- NKS ≥ 80.

## Cobertura histórica de NRS

NRS exige que la prima Norway–Bund se haya normalizado. La serie diaria homogénea del bono noruego a diez años disponible en el backtest comienza en 2019. Por tanto:

- la reversión de 2020 puede probarse de forma completa;
- las ventanas de 2008 y 2014–2015 se marcan como **no disponibles**, no como ausencia de reversión;
- la falta de datos históricos nunca se convierte en cero ni en un falso negativo.

## Guardarraíles

- El agente no ejecuta operaciones ni modifica posiciones.
- Los datos ausentes no se convierten en cero.
- El residual NOK es causal y walk-forward.
- La vía provisional nunca altera fórmulas, pesos ni umbrales.
- Los puntos proxy no forman parte del histórico oficial.
- Un fallo de BCE o EIA degrada la vía rápida sin interrumpir el carril oficial.
- La entrega se basa en estados y cambios, evitando repetir diariamente la misma alerta.
- La ausencia de señal no prueba la ausencia de riesgo estructural.
- Fuentes, fechas, validaciones y resultados quedan versionados en Git.
