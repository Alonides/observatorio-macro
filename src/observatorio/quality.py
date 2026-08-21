"""Reglas transparentes de frescura y calidad."""

from __future__ import annotations

from datetime import date

from .catalog import SeriesSpec


def age_days(observation_date: str, as_of: date) -> int:
    return (as_of - date.fromisoformat(observation_date)).days


def quality_status(spec: SeriesSpec, observation_date: str, as_of: date) -> str:
    age = age_days(observation_date, as_of)
    if age <= spec.stale_after_days:
        return "ok"
    if age <= spec.stale_after_days * 2:
        return "warning"
    return "stale"

