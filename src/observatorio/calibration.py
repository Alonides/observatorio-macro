"""Calibración determinista del componente estadounidense de la duración.

El módulo no decide H0/H1/H2. Convierte cuatro curvas soberanas en un residuo
relativo conforme a la especificación pre-registrada y produce un artefacto
auditable. No requiere bibliotecas numéricas para evitar diferencias de versión
en una regresión pequeña y estable.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date


DEPENDENT = "DGS10"
PEERS = ("IRLTLT01JPM156N", "IRLTLT01DEM156N", "IRLTLT01GBM156N")
MODEL_SERIES = (DEPENDENT, *PEERS)


def _month_number(month: str) -> int:
    year, number = (int(part) for part in month.split("-"))
    return year * 12 + number - 1


def _previous_month(month: str) -> str:
    number = _month_number(month) - 1
    return f"{number // 12:04d}-{number % 12 + 1:02d}"


def closed_month(as_of: date) -> str:
    """Último mes natural enteramente cerrado antes de ``as_of``."""
    return _previous_month(as_of.strftime("%Y-%m"))


def _consecutive(months: list[str]) -> bool:
    return all(
        _month_number(current) - _month_number(previous) == 1
        for previous, current in zip(months, months[1:])
    )


def month_end_rows(series: dict[str, list[dict]], end_month: str | None = None) -> list[dict]:
    """Alinea la última observación de cada mes sin imputar huecos."""
    by_series: dict[str, dict[str, dict]] = {}
    for series_id in MODEL_SERIES:
        selected: dict[str, dict] = {}
        for point in series.get(series_id, []):
            day = str(point.get("date") or "")
            if len(day) < 7 or point.get("value") is None:
                continue
            month = day[:7]
            if end_month is not None and month > end_month:
                continue
            previous = selected.get(month)
            if previous is None or day > previous["date"]:
                selected[month] = {"date": day, "value": float(point["value"])}
        by_series[series_id] = selected

    if any(not by_series[series_id] for series_id in MODEL_SERIES):
        return []
    months = sorted(set.intersection(*(set(by_series[series_id]) for series_id in MODEL_SERIES)))
    return [
        {
            "month": month,
            "observation_dates": {
                series_id: by_series[series_id][month]["date"] for series_id in MODEL_SERIES
            },
            "levels": {
                series_id: by_series[series_id][month]["value"] for series_id in MODEL_SERIES
            },
        }
        for month in months
    ]


def monthly_changes(rows: list[dict]) -> list[dict]:
    output = []
    for previous, current in zip(rows, rows[1:]):
        if not _consecutive([previous["month"], current["month"]]):
            continue
        output.append({
            "month": current["month"],
            "changes": {
                series_id: current["levels"][series_id] - previous["levels"][series_id]
                for series_id in MODEL_SERIES
            },
        })
    return output


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Eliminación de Gauss con pivote parcial para un sistema pequeño."""
    size = len(vector)
    augmented = [list(row) + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Matriz singular en la calibración OLS")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[index][-1] for index in range(size)]


def fit_ols(changes: list[dict]) -> dict:
    if len(changes) < 12:
        raise ValueError("La calibración necesita al menos doce meses completos")
    design = [
        [1.0, *(row["changes"][series_id] for series_id in PEERS)]
        for row in changes
    ]
    outcome = [row["changes"][DEPENDENT] for row in changes]
    width = len(design[0])
    xtx = [[sum(row[i] * row[j] for row in design) for j in range(width)] for i in range(width)]
    xty = [sum(row[i] * value for row, value in zip(design, outcome)) for i in range(width)]
    coefficients = _solve(xtx, xty)
    fitted = [sum(coef * value for coef, value in zip(coefficients, row)) for row in design]
    residuals = [actual - predicted for actual, predicted in zip(outcome, fitted)]
    mean = sum(outcome) / len(outcome)
    sse = sum(value * value for value in residuals)
    sst = sum((value - mean) ** 2 for value in outcome)
    return {
        "intercept": coefficients[0],
        "betas": dict(zip(PEERS, coefficients[1:])),
        "observations": len(changes),
        "r_squared": None if sst == 0 else 1 - sse / sst,
        "rmse": math.sqrt(sse / len(residuals)),
    }


def residual_rows(changes: list[dict], model: dict) -> list[dict]:
    output = []
    for row in changes:
        predicted = model["intercept"] + sum(
            model["betas"][series_id] * row["changes"][series_id] for series_id in PEERS
        )
        output.append({
            "month": row["month"],
            "actual_us_change_pp": row["changes"][DEPENDENT],
            "predicted_us_change_pp": predicted,
            "residual_pp": row["changes"][DEPENDENT] - predicted,
        })
    return output


def rolling_residuals(rows: list[dict], horizon_months: int) -> list[dict]:
    output = []
    for end in range(horizon_months - 1, len(rows)):
        window = rows[end - horizon_months + 1:end + 1]
        months = [row["month"] for row in window]
        if not _consecutive(months):
            continue
        output.append({
            "month": months[-1],
            "residual_sum_pp": sum(row["residual_pp"] for row in window),
        })
    return output


def nearest_rank(values: list[float], percentile: int) -> float:
    if not values:
        raise ValueError("No hay valores para calcular el percentil")
    if not 0 < percentile <= 100:
        raise ValueError("El percentil debe estar en (0, 100]")
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return ordered[rank - 1]


def _episodes(months: list[str]) -> list[dict]:
    if not months:
        return []
    groups: list[list[str]] = [[months[0]]]
    for month in months[1:]:
        if _consecutive([groups[-1][-1], month]):
            groups[-1].append(month)
        else:
            groups.append([month])
    return [
        {"start": group[0], "end": group[-1], "months": len(group)}
        for group in groups
    ]


def activation_report(scores: list[dict], p90: float, p95: float) -> dict:
    p90_months = [row["month"] for row in scores if row["residual_sum_pp"] >= p90]
    p95_months = [row["month"] for row in scores if row["residual_sum_pp"] >= p95]
    persistent = [
        current["month"]
        for previous, current in zip(scores, scores[1:])
        if _consecutive([previous["month"], current["month"]])
        and previous["residual_sum_pp"] >= p95
        and current["residual_sum_pp"] >= p95
    ]
    return {
        "p90_observation_count": len(p90_months),
        "p90_months": p90_months,
        "p90_episodes": _episodes(p90_months),
        "p95_observation_count": len(p95_months),
        "p95_months": p95_months,
        "p95_episodes": _episodes(p95_months),
        "persistent_p95_count": len(persistent),
        "persistent_p95_months": persistent,
    }


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 12)


def _input_hash(rows: list[dict]) -> str:
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_artifact(
    series: dict[str, list[dict]],
    target: dict,
    *,
    as_of: date,
    generated_at: str,
    preregistration_commit: str | None,
    preregistration_methodology_hash: str,
) -> dict:
    end_month = closed_month(as_of)
    rows = month_end_rows(series, end_month=end_month)
    changes = monthly_changes(rows)
    calibration = [
        row for row in changes
        if str(target["calibration_start"])[:7] <= row["month"] <= str(target["calibration_end"])[:7]
    ]
    model = fit_ols(calibration)
    all_residuals = residual_rows(changes, model)
    calibration_end = str(target["calibration_end"])[:7]
    calibration_start = str(target["calibration_start"])[:7]
    out_start = str(target["out_of_sample_start"])[:7]

    horizon_reports = {}
    horizons = [int(target["classifier"]["horizon_months"]), *map(int, target["sensitivity_horizons_months"])]
    for horizon in sorted(set(horizons)):
        scores = rolling_residuals(all_residuals, horizon)
        training_scores = [
            row for row in scores if calibration_start <= row["month"] <= calibration_end
        ]
        p90 = nearest_rank([row["residual_sum_pp"] for row in training_scores], int(target["h0_percentile"]))
        p95 = nearest_rank([row["residual_sum_pp"] for row in training_scores], int(target["h1_percentile"]))
        out_scores = [row for row in scores if row["month"] >= out_start]
        horizon_reports[str(horizon)] = {
            "calibration_observations": len(training_scores),
            "p90_pp": _rounded(p90),
            "p95_pp": _rounded(p95),
            "calibration_activations": activation_report(training_scores, p90, p95),
            "out_of_sample": {
                "start": out_start,
                "end": end_month,
                "observations": len(out_scores),
                "activations": activation_report(out_scores, p90, p95),
                "scores": [
                    {"month": row["month"], "residual_sum_pp": _rounded(row["residual_sum_pp"])}
                    for row in out_scores
                ],
            },
        }

    primary = horizon_reports[str(int(target["classifier"]["horizon_months"]))]
    return {
        "schema_version": 1,
        "model_id": "US_RELATIVE_DURATION_V02",
        "status": "calibrated_candidate",
        "generated_at": generated_at,
        "as_of": as_of.isoformat(),
        "last_closed_month": end_month,
        "preregistration": {
            "frozen_on": str(target["specification_frozen_on"]),
            "git_commit": preregistration_commit,
            "methodology_sha256": preregistration_methodology_hash,
        },
        "sample": {
            "calibration_start": str(target["calibration_start"]),
            "calibration_end": str(target["calibration_end"]),
            "out_of_sample_start": str(target["out_of_sample_start"]),
            "complete_month_end_rows": len(rows),
            "first_month": rows[0]["month"] if rows else None,
            "last_month": rows[-1]["month"] if rows else None,
            "input_sha256": _input_hash(rows),
        },
        "specification": {
            "dependent": DEPENDENT,
            "predictors": list(PEERS),
            "frequency": target["frequency"],
            "observation_rule": target["observation_rule"],
            "currency_treatment": target["currency_treatment"],
            "missing_data": target["missing_data"],
            "estimator": target["regression"]["estimator"],
            "intercept": bool(target["regression"]["intercept"]),
            "quantile_method": target["classifier"]["quantile_method"],
            "primary_horizon_months": int(target["classifier"]["horizon_months"]),
            "selection_across_windows": target["classifier"]["selection_across_windows"],
        },
        "fit": {
            "observations": model["observations"],
            "intercept_pp": _rounded(model["intercept"]),
            "betas": {key: _rounded(value) for key, value in model["betas"].items()},
            "r_squared": _rounded(model["r_squared"]),
            "rmse_pp": _rounded(model["rmse"]),
        },
        "operational_thresholds": {
            "h0_p90_pp": primary["p90_pp"],
            "h1_p95_pp": primary["p95_pp"],
            "h1_persistence_months": int(target["h1_persistence_months"]),
        },
        "horizons": horizon_reports,
        "month_end_inputs": rows,
    }


def live_relative_score(series: dict[str, list[dict]], target: dict, as_of: date) -> dict:
    """Aplica coeficientes congelados a los dos últimos cierres mensuales."""
    result = target.get("calibration_result") or {}
    if not result:
        return {"available": False, "reason": "calibration_result_missing"}
    rows = month_end_rows(series, end_month=closed_month(as_of))
    if not rows:
        return {"available": False, "reason": "model_series_missing"}
    last_closed = closed_month(as_of)
    if rows[-1]["month"] != last_closed:
        return {
            "available": False,
            "reason": "latest_closed_month_incomplete",
            "expected_month": last_closed,
            "latest_complete_month": rows[-1]["month"],
        }
    model = {
        "intercept": float(result["intercept_pp"]),
        "betas": {key: float(value) for key, value in result["betas"].items()},
    }
    residuals = residual_rows(monthly_changes(rows), model)
    horizon = int(target["classifier"]["horizon_months"])
    scores = rolling_residuals(residuals, horizon)
    if not scores or scores[-1]["month"] != last_closed:
        return {"available": False, "reason": "insufficient_consecutive_months"}
    current = scores[-1]
    previous = scores[-2] if len(scores) > 1 and _consecutive([scores[-2]["month"], current["month"]]) else None
    p90 = float(result["h0_p90_pp"])
    p95 = float(result["h1_p95_pp"])
    persistence = int(target["h1_persistence_months"])
    if persistence != 2:
        raise ValueError("El motor v0.2 implementa exactamente dos meses de persistencia")
    return {
        "available": True,
        "month": current["month"],
        "score_pp": current["residual_sum_pp"],
        "previous_month": previous["month"] if previous else None,
        "previous_score_pp": previous["residual_sum_pp"] if previous else None,
        "h0_threshold_p90_pp": p90,
        "h1_threshold_p95_pp": p95,
        "h0_specific": current["residual_sum_pp"] >= p90,
        "h1_specific_persistent": bool(
            previous
            and previous["residual_sum_pp"] >= p95
            and current["residual_sum_pp"] >= p95
        ),
    }


def verify_artifact(artifact: dict, target: dict) -> dict:
    """Reconstruye íntegramente el artefacto desde sus cierres almacenados."""
    series = {series_id: [] for series_id in MODEL_SERIES}
    for row in artifact.get("month_end_inputs", []):
        for series_id in MODEL_SERIES:
            series[series_id].append({
                "date": row["observation_dates"][series_id],
                "value": row["levels"][series_id],
            })
    preregistration = artifact.get("preregistration") or {}
    rebuilt = build_artifact(
        series,
        target,
        as_of=date.fromisoformat(artifact["as_of"]),
        generated_at=artifact["generated_at"],
        preregistration_commit=preregistration.get("git_commit"),
        preregistration_methodology_hash=preregistration.get("methodology_sha256"),
    )
    mismatched = sorted(
        key for key in set(artifact) | set(rebuilt)
        if artifact.get(key) != rebuilt.get(key)
    )
    return {
        "valid": not mismatched,
        "mismatched_sections": mismatched,
        "input_sha256": rebuilt["sample"]["input_sha256"],
        "fit": rebuilt["fit"],
        "operational_thresholds": rebuilt["operational_thresholds"],
    }
