# Debt/NOK Monitor v1.0 · operación

## Qué queda congelado

La versión operativa v1.0 no altera las ecuaciones validadas del núcleo v0.4.1. Añade:

- estados operativos `normal`, `watch`, `alert` y `critical`;
- separación explícita entre `gate_score` y `operational_score` en NRS;
- informe determinista en español;
- panel web específico;
- agente programado con trazabilidad en Git;
- entrega por notificaciones de GitHub, sin credenciales de correo almacenadas.

## Historial operativo del residual

El almacén macro general conserva un histórico compacto destinado al panel público. Después de alinear los calendarios de Noruega, Suecia, Brent y VIX, ese histórico puede quedar por debajo de la muestra mínima exigida por el residual congelado.

El agente no reduce las ventanas para fabricar cobertura. Mantiene en `data/debt_nok/history.json` una caché separada desde 2018 de cinco series oficiales:

- NOK por USD;
- USD por EUR;
- SEK por USD;
- Brent;
- VIX.

En cada ejecución fusiona la caché, el snapshot compacto y la historia obtenida de las fuentes oficiales. Si una fuente falla, conserva las observaciones válidas anteriores y declara el error. Esta capa permite calcular el residual causal con la calibración completa y deja la procedencia y la cobertura registradas.

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
- NKS ≥ 65.

### Crítico

Se activa por cualquiera de los siguientes:

- URR confirma régimen persistente de rechazo;
- NKS ≥ 80;
- NRS está confirmado.

## Guardarraíles

- El agente no ejecuta operaciones ni modifica posiciones.
- Los datos ausentes no se convierten en cero.
- El residual NOK es causal y walk-forward.
- El agente no reduce la muestra mínima cuando falta historia; amplía la caché oficial o mantiene cobertura parcial.
- La entrega se basa en estados y cambios, evitando repetir diariamente la misma alerta.
- La ausencia de señal no prueba la ausencia de riesgo estructural.
- Las fuentes y los resultados quedan versionados en Git.
