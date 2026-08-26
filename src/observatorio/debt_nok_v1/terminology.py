"""Source-accurate terminology for the Debt/NOK v1.0.3 provisional lane.

The first production report used the generic phrase "official proxies" even
when the oil bridge had correctly fallen back to an explicitly labelled
secondary source. This module fixes presentation only: it does not alter source
selection, observations, bridge validation, scores, states or notifications.
"""

from __future__ import annotations

from typing import Callable


_INSTALLED = False


def _replace_source_language(text: str) -> str:
    replacements = (
        (
            "proxies oficiales correlacionados",
            "proxies primarios o secundarios expresamente identificados y validados",
        ),
        (
            "proxies oficiales de vida corta",
            "proxies primarios o secundarios expresamente identificados, de vida corta",
        ),
        (
            "rendimientos de proxies oficiales correlacionados",
            "rendimientos de proxies primarios o secundarios expresamente identificados y validados",
        ),
        (
            "faster official proxy series",
            "faster primary or explicitly labelled secondary proxy series",
        ),
    )
    output = text
    for old, new in replacements:
        output = output.replace(old, new)
    return output


def install_source_terminology() -> None:
    """Patch generated presentation strings once, leaving calculations intact."""
    global _INSTALLED
    if _INSTALLED:
        return

    from . import fast_bridge as bridge_module
    from . import report as report_module

    original_payload: Callable = bridge_module.build_fast_lane_payload
    if not getattr(original_payload, "_source_terminology_safe", False):
        def source_safe_payload(official_result: dict, provisional_result: dict, bridge: dict) -> dict:
            payload = original_payload(official_result, provisional_result, bridge)
            payload["disclaimer"] = (
                "La vía rápida usa proxies primarios o secundarios expresamente "
                "identificados y validados. No confirma por sí sola un cambio de "
                "régimen; la lectura oficial conserva prioridad."
            )
            bridge_payload = payload.get("bridge")
            if isinstance(bridge_payload, dict) and isinstance(bridge_payload.get("method"), str):
                bridge_payload["method"] = _replace_source_language(bridge_payload["method"])
            payload["terminology_note"] = (
                "Primary and secondary provisional sources are distinguished from "
                "the authoritative official lane."
            )
            return payload

        source_safe_payload._source_terminology_safe = True  # type: ignore[attr-defined]
        bridge_module.build_fast_lane_payload = source_safe_payload

    original_render: Callable = report_module.render_markdown
    if not getattr(original_render, "_source_terminology_safe", False):
        def source_safe_render(report: dict) -> str:
            return _replace_source_language(original_render(report))

        source_safe_render._source_terminology_safe = True  # type: ignore[attr-defined]
        report_module.render_markdown = source_safe_render

    _INSTALLED = True


__all__ = ["install_source_terminology"]
