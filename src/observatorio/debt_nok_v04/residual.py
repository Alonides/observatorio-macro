"""Walk-forward NOK residual used by the debt/NOK regime model v0.4.1.

The residual asks a narrow question: is EUR/NOK moving more than would normally
be expected from a common Nordic FX factor (EUR/SEK), Brent and global risk
(VIX)? It is not a forecast and it is not evidence for the null hypothesis.
A low score merely means this particular anomaly detector did not activate.

The implementation is dependency-free and strictly causal:

* coefficients at session t are estimated only from sessions before t;
* the 20-session residual includes t, because it is a contemporaneous signal;
* its robust z-score is standardised only on 20-session residuals before t.

To avoid noisy coefficient churn and keep the historical CI run inexpensive,
the Huber regression is refitted every five common market sessions. Between
refits the most recently estimated past-only coefficients are used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite, log, sqrt
from statistics import median
from typing import Mapping, Sequence


MODEL_VERSION = "0.4.1"
RESIDUAL_SERIES_ID = "NOK_RESIDUAL_Z20"

RESIDUAL_PARAMETERS = {
    "dependent": "daily log return EUR/NOK",
    "factors": (
        "daily log return EUR/SEK",
        "daily log return Brent",
        "daily log return VIX",
    ),
    "training_min_sessions": 504,
    "training_max_sessions": 756,
    "refit_every_sessions": 5,
    "huber_delta": 1.345,
    "huber_max_iterations": 8,
    "residual_sum_sessions": 20,
    "z_history_min_sessions": 252,
    "z_history_max_sessions": 756,
    "z_clip": 20.0,
}


@dataclass(frozen=True)
class ReturnRow:
    date: str
    y: float
    x1: float
    x2: float
    x3: float


@dataclass(frozen=True)
class FitPoint:
    date: str
    intercept: float
    eursek: float
    brent: float
    vix: float
    training_sessions: int

    def to_dict(self) -> dict:
        return asdict(self)


def _point_map(points: Sequence[Mapping[str, object]]) -> dict[str, float]:
    output: dict[str, float] = {}
    for point in points:
        raw_day = point.get("date")
        raw_value = point.get("value")
        if raw_day is None or raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if isfinite(value) and value > 0.0:
            output[str(raw_day)] = value
    return output


def _return_rows(series: Mapping[str, Sequence[Mapping[str, object]]]) -> list[ReturnRow]:
    nokusd = _point_map(series.get("DEXNOUS", ()))
    usdper_eur = _point_map(series.get("DEXUSEU", ()))
    sekusd = _point_map(series.get("DEXSDUS", ()))
    brent = _point_map(series.get("DCOILBRENTEU", ()))
    vix = _point_map(series.get("VIXCLS", ()))
    common = sorted(nokusd.keys() & usdper_eur.keys() & sekusd.keys() & brent.keys() & vix.keys())

    levels: list[tuple[str, float, float, float, float]] = []
    for day in common:
        eurnok = nokusd[day] * usdper_eur[day]
        eursek = sekusd[day] * usdper_eur[day]
        if min(eurnok, eursek, brent[day], vix[day]) <= 0.0:
            continue
        levels.append((day, eurnok, eursek, brent[day], vix[day]))

    rows: list[ReturnRow] = []
    for previous, current in zip(levels, levels[1:]):
        rows.append(ReturnRow(
            date=current[0],
            y=log(current[1] / previous[1]),
            x1=log(current[2] / previous[2]),
            x2=log(current[3] / previous[3]),
            x3=log(current[4] / previous[4]),
        ))
    return rows


def _median_absolute_deviation(values: Sequence[float]) -> tuple[float, float]:
    centre = median(values)
    scale = 1.4826 * median([abs(value - centre) for value in values])
    if scale <= 1e-12:
        if len(values) < 2:
            return centre, 0.0
        mean = sum(values) / len(values)
        scale = sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
    return centre, scale


def _solve_4x4(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    augmented = [matrix[row][:] + [rhs[row]] for row in range(4)]
    # Tiny ridge protects nearly collinear quiet windows without affecting the
    # economically relevant coefficients at normal return scales.
    for index in range(4):
        augmented[index][index] += 1e-12
    for column in range(4):
        pivot = max(range(column, 4), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) <= 1e-18:
            raise ArithmeticError("singular regression matrix")
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(4):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [
                augmented[row][cell] - factor * augmented[column][cell]
                for cell in range(5)
            ]
    return [augmented[row][4] for row in range(4)]


def _weighted_fit(rows: Sequence[ReturnRow], weights: Sequence[float] | None = None) -> list[float]:
    a00 = a01 = a02 = a03 = 0.0
    a11 = a12 = a13 = 0.0
    a22 = a23 = a33 = 0.0
    b0 = b1 = b2 = b3 = 0.0
    for index, row in enumerate(rows):
        weight = 1.0 if weights is None else weights[index]
        x1, x2, x3, y = row.x1, row.x2, row.x3, row.y
        a00 += weight
        a01 += weight * x1
        a02 += weight * x2
        a03 += weight * x3
        a11 += weight * x1 * x1
        a12 += weight * x1 * x2
        a13 += weight * x1 * x3
        a22 += weight * x2 * x2
        a23 += weight * x2 * x3
        a33 += weight * x3 * x3
        b0 += weight * y
        b1 += weight * x1 * y
        b2 += weight * x2 * y
        b3 += weight * x3 * y
    matrix = [
        [a00, a01, a02, a03],
        [a01, a11, a12, a13],
        [a02, a12, a22, a23],
        [a03, a13, a23, a33],
    ]
    return _solve_4x4(matrix, [b0, b1, b2, b3])


def _predict(row: ReturnRow, beta: Sequence[float]) -> float:
    return beta[0] + beta[1] * row.x1 + beta[2] * row.x2 + beta[3] * row.x3


def _huber_fit(rows: Sequence[ReturnRow]) -> list[float]:
    beta = _weighted_fit(rows)
    delta = float(RESIDUAL_PARAMETERS["huber_delta"])
    max_iterations = int(RESIDUAL_PARAMETERS["huber_max_iterations"])
    for _ in range(max_iterations):
        residuals = [row.y - _predict(row, beta) for row in rows]
        centre, scale = _median_absolute_deviation(residuals)
        if not isfinite(scale) or scale <= 1e-12:
            break
        cutoff = delta * scale
        weights = [
            1.0 if abs(residual - centre) <= cutoff
            else cutoff / abs(residual - centre)
            for residual in residuals
        ]
        candidate = _weighted_fit(rows, weights)
        if max(abs(candidate[index] - beta[index]) for index in range(4)) <= 1e-10:
            beta = candidate
            break
        beta = candidate
    return beta


def build_nok_residual(
    series: Mapping[str, Sequence[Mapping[str, object]]],
) -> dict:
    rows = _return_rows(series)
    minimum = int(RESIDUAL_PARAMETERS["training_min_sessions"])
    maximum = int(RESIDUAL_PARAMETERS["training_max_sessions"])
    refit_every = int(RESIDUAL_PARAMETERS["refit_every_sessions"])
    residual_window = int(RESIDUAL_PARAMETERS["residual_sum_sessions"])
    z_minimum = int(RESIDUAL_PARAMETERS["z_history_min_sessions"])
    z_maximum = int(RESIDUAL_PARAMETERS["z_history_max_sessions"])
    z_clip = float(RESIDUAL_PARAMETERS["z_clip"])

    residuals: list[tuple[str, float]] = []
    coefficients: list[FitPoint] = []
    beta: list[float] | None = None
    for index in range(minimum, len(rows)):
        if beta is None or (index - minimum) % refit_every == 0:
            start = max(0, index - maximum)
            training = rows[start:index]
            try:
                beta = _huber_fit(training)
            except ArithmeticError:
                beta = None
                continue
            coefficients.append(FitPoint(
                date=rows[index].date,
                intercept=beta[0],
                eursek=beta[1],
                brent=beta[2],
                vix=beta[3],
                training_sessions=len(training),
            ))
        if beta is not None:
            residuals.append((rows[index].date, rows[index].y - _predict(rows[index], beta)))

    cumulative: list[tuple[str, float]] = []
    running = 0.0
    queue: list[float] = []
    for day, value in residuals:
        queue.append(value)
        running += value
        if len(queue) > residual_window:
            running -= queue.pop(0)
        if len(queue) == residual_window:
            cumulative.append((day, running))

    z_points: list[dict] = []
    for index, (day, value) in enumerate(cumulative):
        history = [item[1] for item in cumulative[max(0, index - z_maximum):index]]
        if len(history) < z_minimum:
            continue
        centre, scale = _median_absolute_deviation(history)
        if not isfinite(scale) or scale <= 1e-12:
            continue
        z_value = max(-z_clip, min(z_clip, (value - centre) / scale))
        z_points.append({"date": day, "value": z_value})

    return {
        "model_version": MODEL_VERSION,
        "series_id": RESIDUAL_SERIES_ID,
        "points": z_points,
        "daily_residual": [{"date": day, "value": value} for day, value in residuals],
        "cumulative_residual_20": [{"date": day, "value": value} for day, value in cumulative],
        "coefficient_path": [point.to_dict() for point in coefficients],
        "coverage": {
            "common_return_sessions": len(rows),
            "daily_residual_sessions": len(residuals),
            "z_scored_sessions": len(z_points),
            "start": z_points[0]["date"] if z_points else None,
            "end": z_points[-1]["date"] if z_points else None,
        },
        "parameters": RESIDUAL_PARAMETERS,
        "no_lookahead": True,
        "method_note": (
            "Positive z means NOK weakened more than the walk-forward model expected; "
            "negative z means it strengthened more than expected. The signal does not "
            "establish or disprove a causal macro hypothesis."
        ),
    }


def attach_nok_residual(
    series: Mapping[str, Sequence[Mapping[str, object]]],
) -> tuple[dict, dict]:
    supplied = series.get(RESIDUAL_SERIES_ID)
    if supplied:
        enriched = dict(series)
        return enriched, {
            "model_version": MODEL_VERSION,
            "series_id": RESIDUAL_SERIES_ID,
            "source": "supplied",
            "coverage": {
                "z_scored_sessions": len(supplied),
                "start": supplied[0].get("date") if supplied else None,
                "end": supplied[-1].get("date") if supplied else None,
            },
            "parameters": RESIDUAL_PARAMETERS,
            "no_lookahead": None,
        }
    result = build_nok_residual(series)
    enriched = dict(series)
    enriched[RESIDUAL_SERIES_ID] = result["points"]
    diagnostics = {key: value for key, value in result.items() if key not in {
        "points", "daily_residual", "cumulative_residual_20", "coefficient_path"
    }}
    diagnostics["source"] = "calculated"
    if result["coefficient_path"]:
        diagnostics["latest_coefficients"] = result["coefficient_path"][-1]
    return enriched, diagnostics


__all__ = [
    "MODEL_VERSION",
    "RESIDUAL_PARAMETERS",
    "RESIDUAL_SERIES_ID",
    "attach_nok_residual",
    "build_nok_residual",
]
