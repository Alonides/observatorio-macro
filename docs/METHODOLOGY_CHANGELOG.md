# Registro metodológico

## v0.1 · preservada

- Commit de referencia: `63a1f6e6fd3ae47cf8f9b6aa102ce2e1c9c6eb7a`.
- Rama: `archive/v0.1`.
- Conserva la primera implementación y sus resultados. No se recalcula con reglas nuevas.

Limitaciones que motivan v0.2:

- H0 y H2 no coincidían con las definiciones del ensayo.
- H0 del ensayo carecía de salida positiva y H2 era lógicamente inalcanzable.
- Una sola ventana de cambio era ciega a la degradación estructural lenta.
- VIX no medía pérdida de función refugio y el capex no representaba emisión por duración.
- Deuda bruta y deuda en manos del público no estaban separadas.
- Faltaban numerario oro, huella metodológica y fechas de congelación por parámetro.

## v0.2.0-dev · 21 de agosto de 2026

- Rama: `feature/methodology-v0.2`.
- Estado: desarrollo; todavía no sustituye la versión pública.
- Semántica: `MEIR-MON-002-A1`, *El precio del privilegio*, v0.5.
- Fuente ejecutable: `methodology.yml`; el SHA-256 se calcula sobre JSON canónico.

Cambios:

1. H0 = prima estadounidense de oferta/plazo; H1 = pérdida específica de confianza; H2 = reprecio global; `MIXED` se separa.
2. H0 requiere prueba positiva. La ausencia de H1 conduce como máximo a `INDETERMINATE`.
3. La triple señal se declara alarma. Sus activaciones de junio de 2009 y febrero de 2011 son compatibles con reflación y no se contabilizan como aciertos de H1.
4. S&P 500, OAS IG y rendimiento IG se incorporan como contexto, sin imponer «bolsa abajo» como condición necesaria.
5. Se añaden motor estructural separado, deuda en manos del público y capa de numerario oro.
6. Cada observación distingue periodo, publicación cuando exista, recogida y revisión.
7. El parámetro de especificidad estadounidense permanece `transitional` hasta calibrar el modelo relativo.
8. El JGB a diez años une el histórico oficial del MOF con el mes corriente; deja de depender de trece observaciones aisladas.

Regla de cambio: un parámetro nuevo recibe fecha de congelación y corte de calibración antes de evaluar datos posteriores. Toda recalibración crea una nueva versión; no modifica este registro retrospectivamente.

## 2026-08-22 · pre-registro del modelo relativo v0.2

- Se congelan antes de estimar la cesta Japón–Alemania–Reino Unido, la frecuencia mensual, el OLS con intercepto y el uso de variaciones de rendimientos en moneda local.
- Se fija como estadístico operativo la suma móvil de tres residuos mensuales; dos y cuatro meses quedan reservados a sensibilidad y no pueden competir por el máximo.
- Se fija el método de rango más próximo para p90/p95 y la exigencia de dos cierres consecutivos sobre p95 para la especificidad fuerte de H1.
- El tramo 2003–2024 estima; 2025–presente solo valida fuera de muestra.
- En el momento de esta entrada no se habían calculado coeficientes, umbrales ni activaciones.
