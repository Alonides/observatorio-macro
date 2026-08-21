"""Catálogo versionado de series y procedencia.

Los identificadores son internos y estables. La fuente declarada describe al
productor real del dato, aunque el identificador conserve un alias histórico
conocido por economistas (por ejemplo, ``DGS10`` o ``UNRATE``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SeriesSpec:
    id: str
    title: str
    group: str
    unit: str
    frequency: str
    stale_after_days: int
    source: str
    source_url: str

    def to_dict(self) -> dict:
        return asdict(self)


TREASURY_RATES = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"
FED_DDP = "https://www.federalreserve.gov/datadownload/"
FED_H41 = "https://www.federalreserve.gov/releases/h41/current/h41.htm"
FED_H10 = "https://www.federalreserve.gov/releases/h10/current/"
NYFED = "https://markets.newyorkfed.org/"
EIA = "https://www.eia.gov/opendata/"
SEC = "https://data.sec.gov/"


SERIES: tuple[SeriesSpec, ...] = (
    # Estados Unidos: curva nominal, real e inflación implícita.
    SeriesSpec("DGS3MO", "Treasury EE. UU. 3 meses", "Deuda EE. UU.", "%", "daily", 7, "U.S. Treasury", TREASURY_RATES),
    SeriesSpec("DGS2", "Treasury EE. UU. 2 años", "Deuda EE. UU.", "%", "daily", 7, "U.S. Treasury", TREASURY_RATES),
    SeriesSpec("DGS10", "Treasury EE. UU. 10 años", "Deuda EE. UU.", "%", "daily", 7, "U.S. Treasury", TREASURY_RATES),
    SeriesSpec("DGS30", "Treasury EE. UU. 30 años", "Deuda EE. UU.", "%", "daily", 7, "U.S. Treasury", TREASURY_RATES),
    SeriesSpec("DFII10", "TIPS real EE. UU. 10 años", "Deuda EE. UU.", "% real", "daily", 7, "U.S. Treasury", TREASURY_RATES),
    SeriesSpec("T10YIE", "Breakeven inflación EE. UU. 10 años", "Inflación", "%", "daily", 7, "Derivado Treasury nominal − real", TREASURY_RATES),
    # Dinero, liquidez y tensión financiera.
    SeriesSpec("SOFR", "SOFR", "Liquidez", "%", "daily", 7, "Federal Reserve Bank of New York", NYFED),
    SeriesSpec("IORB", "Interés sobre saldos de reserva", "Liquidez", "%", "daily", 7, "Federal Reserve Board", FED_DDP),
    SeriesSpec("RRPONTSYD", "Reverse repo overnight", "Liquidez", "miles de millones USD", "daily", 7, "Federal Reserve Bank of New York", NYFED),
    SeriesSpec("WALCL", "Balance total de la Reserva Federal", "Liquidez", "millones USD", "weekly", 14, "Federal Reserve Board H.4.1", FED_H41),
    SeriesSpec("WTREGEN", "Cuenta General del Tesoro", "Liquidez", "millones USD", "weekly", 14, "Federal Reserve Board H.4.1", FED_H41),
    SeriesSpec("VIXCLS", "VIX", "Riesgo", "índice", "daily", 7, "Cboe Global Markets", "https://www.cboe.com/tradable_products/vix/vix_historical_data/"),
    # Dólar, divisas, reservas alternativas y energía.
    SeriesSpec("DTWEXBGS", "Índice amplio del dólar", "Divisas", "índice", "daily", 7, "Federal Reserve Board H.10", FED_H10),
    SeriesSpec("DEXUSEU", "USD por EUR", "Divisas", "USD/EUR", "daily", 7, "Federal Reserve Board H.10", FED_H10),
    SeriesSpec("DEXNOUS", "NOK por USD", "Noruega", "NOK/USD", "daily", 7, "Federal Reserve Board H.10", FED_H10),
    SeriesSpec("DEXJPUS", "JPY por USD", "Japón", "JPY/USD", "daily", 7, "Federal Reserve Board H.10", FED_H10),
    SeriesSpec("DEXCHUS", "CNY por USD", "China", "CNY/USD", "daily", 7, "Federal Reserve Board H.10", FED_H10),
    SeriesSpec("GOLDAMGBD228NLBM", "Oro fixing AM Londres", "Activos reserva", "USD/onza", "daily", 7, "LBMA", "https://www.lbma.org.uk/prices-and-data/precious-metal-prices"),
    SeriesSpec("CBBTCUSD", "Bitcoin", "Activos reserva", "USD/BTC", "daily", 7, "CoinGecko", "https://www.coingecko.com/en/coins/bitcoin"),
    SeriesSpec("DCOILBRENTEU", "Petróleo Brent", "Energía", "USD/barril", "daily", 10, "U.S. Energy Information Administration", EIA),
    SeriesSpec("DHHNGSP", "Gas natural Henry Hub", "Energía", "USD/MMBtu", "daily", 10, "U.S. Energy Information Administration", EIA),
    # Anclas soberanas internacionales, todas diarias o de día hábil.
    SeriesSpec("IRLTLT01JPM156N", "Japón: JGB 10 años", "Duración global", "%", "daily", 10, "Ministry of Finance Japan", "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"),
    SeriesSpec("IRLTLT01DEM156N", "Alemania: Bund 10 años", "Duración global", "%", "daily", 10, "Deutsche Bundesbank", "https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields"),
    SeriesSpec("IRLTLT01GBM156N", "Reino Unido: gilt 10 años", "Duración global", "%", "daily", 10, "Bank of England", "https://www.bankofengland.co.uk/boeapps/database/"),
    SeriesSpec("IRLTLT01NOM156N", "Noruega: bono público 10 años", "Noruega", "%", "daily", 10, "Norges Bank", "https://www.norges-bank.no/en/topics/Statistics/norwegian-government-securities/generiske-statsrenter/"),
    SeriesSpec("IRLTLT01EZM156N", "Eurozona: spot soberano AAA 10 años", "Duración global", "%", "daily", 10, "European Central Bank", "https://data.ecb.europa.eu/data/datasets/YC/YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"),
    # Capacidad fiscal y denominador económico.
    SeriesSpec("GFDEBTN", "Deuda federal bruta de EE. UU.", "Fiscal", "millones USD", "daily", 7, "U.S. Treasury Fiscal Data", "https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/"),
    SeriesSpec("A091RC1Q027SBEA", "Intereses federales pagados", "Fiscal", "miles de millones USD SAAR", "quarterly", 140, "BEA · espejo DBnomics", "https://db.nomics.world/BEA/NIPA-T30200/A091RC-Q"),
    SeriesSpec("GDP", "PIB nominal de EE. UU.", "Fiscal", "miles de millones USD SAAR", "quarterly", 140, "BEA · espejo DBnomics", "https://db.nomics.world/BEA/NIPA-T10105/A191RC-Q"),
    SeriesSpec("CPIAUCSL", "IPC de EE. UU.", "Inflación", "índice", "monthly", 45, "U.S. Bureau of Labor Statistics", "https://www.bls.gov/cpi/data.htm"),
    SeriesSpec("UNRATE", "Desempleo de EE. UU.", "Economía real", "%", "monthly", 45, "U.S. Bureau of Labor Statistics", "https://www.bls.gov/cps/data.htm"),
    # Inversión productiva que compite por capital. Último ejercicio fiscal
    # comunicado, no estimación diaria ni capitalización bursátil.
    SeriesSpec("CAPEX_MSFT", "Microsoft: capex último ejercicio", "Capacidad productiva", "miles de millones USD", "annual", 500, "SEC Company Facts", SEC),
    SeriesSpec("CAPEX_GOOG", "Alphabet: capex último ejercicio", "Capacidad productiva", "miles de millones USD", "annual", 500, "SEC Company Facts", SEC),
    SeriesSpec("CAPEX_AMZN", "Amazon: capex último ejercicio", "Capacidad productiva", "miles de millones USD", "annual", 500, "SEC Company Facts", SEC),
    SeriesSpec("CAPEX_META", "Meta: capex último ejercicio", "Capacidad productiva", "miles de millones USD", "annual", 500, "SEC Company Facts", SEC),
    SeriesSpec("CAPEX_ORCL", "Oracle: capex último ejercicio", "Capacidad productiva", "miles de millones USD", "annual", 500, "SEC Company Facts", SEC),
)

SERIES_BY_ID = {item.id: item for item in SERIES}
