"""Deterministic Spanish reports for the operational Debt/NOK monitor."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo

from .monitor import LEVELS, MODEL_VERSION, evaluate_operational, previous_block_dates


SCHEDULE = {
    "daily_monitor": "Martes a viernes, 07:00 UTC",
    "weekly_report": "Lunes, 07:30 UTC",
    "oslo_note": "08:00/08:30 en invierno y 09:00/09:30 en verano (Europa/Oslo)",
    "delivery": "Panel web y notificación de GitHub asignada a Alonides",
}


def _score(result: dict, key: str) -> float:
    try:
        return float(result["operational"]["blocks"][key]["score"])
    except (KeyError, TypeError, ValueError):
        return 0.0


def _fmt(value, digits: int = 2, suffix: str = "") -> str:
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _value(result: dict, path: tuple[str, ...]):
    current = result
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _local_datetime(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(ZoneInfo("Europe/Oslo"))


def _headline(current: dict) -> str:
    level = current["operational"]["level"]
    if level == "critical":
        return "Configuración crítica: revisión humana inmediata"
    if level == "alert":
        return "Alerta material en el sistema deuda/dólar o en NOK"
    if level == "watch":
        return "Vigilancia reforzada: señales incompletas o no persistentes"
    return "Sin configuración activa de crisis; vigilancia estructural normal"


def _delta(current: dict, previous: dict, key: str) -> float:
    return round(_score(current, key) - _score(previous, key), 2)


def _lag_text(value) -> str:
    try:
        lag = int(value)
    except (TypeError, ValueError):
        return "no disponible"
    if lag <= 0:
        return "al día"
    if lag == 1:
        return "1 día hábil"
    return f"{lag} días hábiles"


def build_report(
    series: Mapping[str, Sequence[Mapping[str, object]]],
    mode: str = "daily",
    generated_at: str | None = None,
) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    local = _local_datetime(generated_at)
    current = evaluate_operational(series)
    previous_dates = previous_block_dates(series, current.get("block_asof", {}), sessions=5)
    previous = evaluate_operational(series, block_asof=previous_dates)
    blocks = ("URP", "URR", "DSS", "NKS", "NRS")
    deltas = {key: _delta(current, previous, key) for key in blocks}
    level = current["operational"]["level"]
    alert = {
        "level": level,
        "rank": LEVELS[level]["rank"],
        "label": LEVELS[level]["label"],
        "tone": LEVELS[level]["tone"],
        "material": current["operational"]["notification_required"],
    }
    report = {
        "schema_version": 2,
        "model_version": MODEL_VERSION,
        "generated_at": generated_at,
        "generated_at_oslo": local.isoformat(),
        "report_date": local.date().isoformat(),
        "mode": mode,
        "asof": current.get("asof"),
        "block_asof": current.get("block_asof", {}),
        "previous_asof": previous.get("asof"),
        "previous_block_asof": previous_dates,
        "freshness": current.get("freshness", {}),
        "alert": alert,
        "headline": _headline(current),
        "summary": current["operational"]["summary"],
        "reasons": current["operational"]["reasons"],
        "current": current,
        "previous": previous,
        "score_deltas_5_sessions": deltas,
        "schedule": SCHEDULE,
        "delivery_note": (
            "El informe periódico se publica en el panel. GitHub crea o comenta "
            "un hilo asignado a Alonides, que normalmente genera un aviso por correo."
        ),
    }
    report["markdown"] = render_markdown(report)
    report["notification_title"] = f"Debt/NOK · {alert['label']} · {report['report_date']}"
    return report


def render_markdown(report: dict) -> str:
    current = report["current"]
    previous = report["previous"]
    level = report["alert"]["label"]
    freshness = report.get("freshness", {})
    fresh_blocks = freshness.get("blocks", {}) if isinstance(freshness, dict) else {}
    generated = report.get("generated_at_oslo", report.get("generated_at", ""))
    generated_display = generated[:16].replace("T", " ") if generated else "—"
    latest_input = freshness.get("latest_input_date") or report.get("asof") or "—"
    oldest = freshness.get("oldest_block") or "—"
    max_lag = freshness.get("maximum_business_day_lag")

    lines = [
        f"# Informe Debt/NOK · {report['report_date']}",
        "",
        f"**Estado operativo: {level}.** {report['headline']}",
        "",
        report["summary"],
        "",
        f"**Actualizado en Oslo:** {generated_display}. **Último dato de mercado:** {latest_input}. "
        f"**Bloque más retrasado:** {oldest} ({_lag_text(max_lag)}).",
        "",
        "## Frescura de los bloques",
        "",
        "| Bloque | Datos a | Retraso aproximado | Estado |",
        "|---|---|---:|---|",
    ]
    for key in ("URP", "URR", "DSS", "NKS", "NRS"):
        item = fresh_blocks.get(key, {})
        lines.append(
            f"| {key} | {item.get('asof') or '—'} | "
            f"{_lag_text(item.get('business_day_lag'))} | {item.get('label') or 'No disponible'} |"
        )

    lines.extend([
        "",
        "## Panel de bloques",
        "",
        "| Bloque | Actual | Estado | Datos a | Hace 5 sesiones | Δ |",
        "|---|---:|---|---|---:|---:|",
    ])
    for key in ("URP", "URR", "DSS", "NKS", "NRS"):
        block = current["operational"]["blocks"][key]
        old = previous["operational"]["blocks"][key]
        delta = report["score_deltas_5_sessions"][key]
        lines.append(
            f"| {key} · {block['label']} | {block['score']:.2f} | "
            f"{block['state']} | {block.get('asof') or '—'} | {old['score']:.2f} | {delta:+.2f} |"
        )

    lines.extend([
        "",
        "## Variables discriminantes",
        "",
        f"- Treasury 30 años, cambio 10 sesiones: **{_fmt(_value(current, ('urp', 'values', 'ust30_change_10_bp')), 1, ' pb')}**.",
        f"- Dólar amplio, caída 10 sesiones: **{_fmt(_value(current, ('urp', 'values', 'broad_usd_drop_10_pct')), 2, ' %')}**.",
        f"- VIX: **{_fmt(_value(current, ('urp', 'values', 'vix')), 2)}**.",
        f"- EUR/NOK, cambio 20 sesiones: **{_fmt(_value(current, ('nks', 'values', 'eurnok_change_20_pct')), 2, ' %')}**.",
        f"- Debilidad NOK frente a SEK, 20 sesiones: **{_fmt(_value(current, ('nks', 'values', 'noksek_change_20_pct')), 2, ' %')}**.",
        f"- Residual NOK: **{_fmt(_value(current, ('nks', 'values', 'nok_residual_z20')), 2, 'σ')}**.",
        f"- Norway–Bund, cambio 20 sesiones: **{_fmt(_value(current, ('nks', 'values', 'norway_bund_change_20_bp')), 1, ' pb')}**.",
        "",
        "## Lectura operativa",
        "",
    ])
    for reason in report["reasons"]:
        lines.append(f"- {reason}.")
    lines.extend([
        "",
        "## Método y límites",
        "",
        "El agente es determinista y auditable. No ejecuta operaciones ni ofrece recomendaciones de inversión. "
        "Separa rechazo del dólar, escasez de dólares, estrés NOK y reversión NOK. Cada bloque usa su propia "
        "fecha completa de datos; los datos ausentes no se imputan como cero.",
        "",
        "La frescura no altera scores, pesos ni umbrales. Un bloque retrasado conserva su última lectura válida y "
        "muestra expresamente la fecha y el desfase, en vez de retrasar silenciosamente todo el informe.",
        "",
        f"Cadencia: {SCHEDULE['weekly_report']} para el informe completo; {SCHEDULE['daily_monitor']} para comprobaciones intermedias y alertas materiales.",
    ])
    return "\n".join(lines) + "\n"


__all__ = ["SCHEDULE", "build_report", "render_markdown"]
