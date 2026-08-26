# Debt/NOK Monitor v1.0.2 · operación

## Qué queda congelado

La versión operativa v1.0.2 no altera las ecuaciones validadas del núcleo v0.4.1. Mantiene:

- estados operativos `normal`, `watch`, `alert` y `critical`;
- separación explícita entre `gate_score` y `operational_score` en NRS;
- informe determinista en español;
- panel web específico;
- agente programado con trazabilidad en Git;
- entrega por notificaciones de GitHub, sin credenciales de correo almacenadas.

La corrección v1.0.1 distinguió una **reversión NOK confirmada** de un deterioro crítico: NRS genera una alerta material de cambio de régimen, pero no convierte por sí solo el panel en rojo. También impide interpretar periodos sin historia Norway–Bund como resultados negativos de NRS.

La mejora v1.0.2 separa la **fecha del informe** de la **fecha de los datos** y evita que la fuente más lenta retrase silenciosamente todos los bloques.

## Fechas y frescura por bloque

Cada bloque se evalúa en su última fecha completa propia:

- **URP:** Treasury 30 años, dólar amplio, riesgo y prima relativa USA–Bund.
- **URR:** fecha URP más oro y rendimiento real cuando están disponibles.
- **DSS:** Treasury 30 años, dólar amplio y riesgo.
- **NKS:** EUR/NOK, NOK/SEK, residual NOK y funding disponible.
- **NRS:** EUR/NOK, NOK/SEK, Norway–Bund y Brent; el residual se incorpora cuando existe y sigue siendo obligatorio para confirmar una reversión.

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

La fecha que encabeza el informe es la fecha de generación en `Europe/Oslo`. La fecha de mercado más reciente y las fechas de cada bloque se presentan por separado.

## Comparación a cinco sesiones

El cambio frente a hace cinco sesiones se calcula también por bloque:

- URP, URR y DSS retroceden cinco observaciones de Treasury 30 años desde su propia fecha;
- NKS y NRS retroceden cinco observaciones de EUR/NOK desde su propia fecha.

Así se evita comparar un bloque reciente con otro que todavía depende de una fuente anterior.

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

Desde v1.0.2, el nombre del informe histórico usa la fecha de generación en Oslo, no la fecha del bloque más lento.

El informe semanal se añade como comentario a un único issue titulado **Debt/NOK · informes periódicos**, asignado a `Alonides`. GitHub normalmente envía una notificación por correo al usuario asignado, de acuerdo con sus preferencias de notificación. Las alertas materiales se abren como issues independientes.

No se usan secretos SMTP ni claves de un proveedor de correo.

## Niveles operativos

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

La última condición es una señal material de cambio de régimen y exige revisión humana, pero no implica por sí sola un agravamiento sistémico.

### Crítico

Se activa por cualquiera de los siguientes:

- URR confirma régimen persistente de rechazo;
- NKS ≥ 80.

## Cobertura histórica de NRS

NRS exige explícitamente que la prima Norway–Bund se haya normalizado. La serie diaria homogénea del bono noruego a diez años disponible en el backtest comienza en 2019. Por tanto:

- la reversión de 2020 puede probarse de forma completa;
- las ventanas de 2008 y 2014–2015 se marcan como **no disponibles**, no como ausencia de reversión;
- la falta de datos históricos nunca se convierte en cero ni en un falso negativo.

## Guardarraíles

- El agente no ejecuta operaciones ni modifica posiciones.
- Los datos ausentes no se convierten en cero.
- El residual NOK es causal y walk-forward.
- La frescura modifica exclusivamente la fecha de evaluación y su presentación; no cambia fórmulas, pesos ni umbrales.
- La entrega se basa en estados y cambios, evitando repetir diariamente la misma alerta.
- La ausencia de señal no prueba la ausencia de riesgo estructural.
- Las fuentes, fechas y resultados quedan versionados en Git.
