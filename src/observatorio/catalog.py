"""Catálogo versionado de series.

La primera versión usa el CSV público de FRED, que no requiere clave. Cada
entrada declara procedencia, frecuencia esperada y tolerancia de antigüedad.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class SeriesSpec:
    id: str
    title: str
    group: str
    unit: str
    frequency: str
    stale_after_days: int
    source: str = "FRED"

    def to_dict(self) -> dict:
        return asdict(self)


SERIES: tuple[SeriesSpec, ...] = (
    # Estados Unidos: curva nominal, real e inflación implícita.
    SeriesSpec("DGS3MO", "Treasury EE. UU. 3 meses", "Deuda EE. UU.", "%", "daily", 7),
    SeriesSpec("DGS2", "Treasury EE. UU. 2 años", "Deuda EE. UU.", "%", "daily", 7),
    SeriesSpec("DGS10", "Treasury EE. UU. 10 años", "Deuda EE. UU.", "%", "daily", 7),
    SeriesSpec("DGS30", "Treasury EE. UU. 30 años", "Deuda EE. UU.", "%", "daily", 7),
    SeriesSpec("DFII10", "TIPS real EE. UU. 10 años", "Deuda EE. UU.", "% real", "daily", 7),
    SeriesSpec("T10YIE", "Breakeven inflación EE. UU. 10 años", "Inflación", "%", "daily", 7),
    # Dinero, liquidez y tensión financiera.
    SeriesSpec("SOFR", "SOFR", "Liquidez", "%", "daily", 7),
    SeriesSpec("IORB", "Interés sobre saldos de reserva", "Liquidez", "%", "daily", 7),
    SeriesSpec("RRPONTSYD", "Reverse repo overnight", "Liquidez", "miles de millones USD", "daily", 7),
    SeriesSpec("WALCL", "Balance total de la Reserva Federal", "Liquidez", "millones USD", "weekly", 14),
    SeriesSpec("WTREGEN", "Cuenta General del Tesoro", "Liquidez", "millones USD", "weekly", 14),
    SeriesSpec("STLFSI4", "Índice de tensión financiera St. Louis", "Liquidez", "índice", "weekly", 14),
    SeriesSpec("VIXCLS", "VIX", "Riesgo", "índice", "daily", 7),
    # Dólar, divisas, reservas alternativas y energía.
    SeriesSpec("DTWEXBGS", "Índice amplio del dólar", "Divisas", "índice", "daily", 7),
    SeriesSpec("DEXUSEU", "USD por EUR", "Divisas", "USD/EUR", "daily", 7),
    SeriesSpec("DEXNOUS", "NOK por USD", "Noruega", "NOK/USD", "daily", 7),
    SeriesSpec("DEXJPUS", "JPY por USD", "Japón", "JPY/USD", "daily", 7),
    SeriesSpec("DEXCHUS", "CNY por USD", "China", "CNY/USD", "daily", 7),
    SeriesSpec("GOLDAMGBD228NLBM", "Oro fixing AM Londres", "Activos reserva", "USD/onza", "daily", 7),
    SeriesSpec("CBBTCUSD", "Bitcoin", "Activos reserva", "USD/BTC", "daily", 7),
    SeriesSpec("DCOILBRENTEU", "Petróleo Brent", "Energía", "USD/barril", "daily", 7),
    SeriesSpec("DHHNGSP", "Gas natural Henry Hub", "Energía", "USD/MMBtu", "daily", 7),
    # Anclas soberanas internacionales. Las series OECD son mensuales: el panel
    # muestra su fecha real y nunca las presenta como cotización diaria.
    SeriesSpec("IRLTLT01JPM156N", "Japón: bono público largo", "Duración global", "%", "monthly", 62),
    SeriesSpec("IRLTLT01DEM156N", "Alemania: bono público largo", "Duración global", "%", "monthly", 62),
    SeriesSpec("IRLTLT01GBM156N", "Reino Unido: bono público largo", "Duración global", "%", "monthly", 62),
    SeriesSpec("IRLTLT01NOM156N", "Noruega: bono público largo", "Noruega", "%", "monthly", 62),
    SeriesSpec("IRLTLT01EZM156N", "Eurozona: bono público largo", "Duración global", "%", "monthly", 62),
    # Capacidad fiscal y denominador económico.
    SeriesSpec("GFDEBTN", "Deuda federal bruta de EE. UU.", "Fiscal", "millones USD", "quarterly", 140),
    SeriesSpec("A091RC1Q027SBEA", "Intereses federales pagados", "Fiscal", "miles de millones USD SAAR", "quarterly", 140),
    SeriesSpec("GDP", "PIB nominal de EE. UU.", "Fiscal", "miles de millones USD SAAR", "quarterly", 140),
    SeriesSpec("CPIAUCSL", "IPC de EE. UU.", "Inflación", "índice", "monthly", 45),
    SeriesSpec("UNRATE", "Desempleo de EE. UU.", "Economía real", "%", "monthly", 45),
)

SERIES_BY_ID = {item.id: item for item in SERIES}

