# Debt and NOK Regime Model v0.4

## Empirical correction

The frozen v0.3 specification was run over every available session from 2006.
It correctly rejected the classic controls and detected April 2025, but it also
produced false US-rejection pulses during recovery phases in 2009, October
2011 and October 2022.

The common cause was the risk gate: v0.3 accepted a high VIX even when VIX was
falling. A high but declining VIX describes the aftermath of stress, not a new
risk-off onset.

v0.4 therefore requires, over ten sessions:

- US 30-year yield at least +20 basis points;
- broad dollar at least -1 percent;
- and either an S&P 500 decline of at least 3 percent, when available, or:
  - VIX at least 25; and
  - VIX rising by at least 5 points or 20 percent.

The VIX level still contributes to severity after the gate opens. It cannot
open the gate merely by remaining elevated.

## Continuous result that motivated v0.4

After applying this correction to the first historical dataset, URP produced
one episode above 50:

- 11-16 April 2025;
- four sessions;
- peak score about 59;
- URR classified it as a rejection pulse, not a persistent rejection regime.

Lehman 2008, the US downgrade of 2011, the 2013 taper tantrum, Q4 2018, Covid
2020, the 2022 inflation shock and the 2023 banking stress produced no URP
episode above 50. DSS separately detected the dollar shortages of 2008 and
2020, as intended.

## Data corrections

- Federal Reserve H.10 now requests 6,000 observations instead of 20,000.
- EIA Brent is paginated beyond the 5,000-row response limit.
- URR is reported separately in the continuous output.
- Missing Norway-Bund, NOK residual and NIBOR-OIS history remains explicitly
  missing; it is never fabricated or silently converted into zero.

## Repository layout

The v0.4 implementation is isolated under:

- `src/observatorio/debt_nok_v04/`
- `scripts/backtest_regimes_v04.py`
- `tests/test_debt_nok_v04.py`
- `.github/workflows/backtest_v04.yml`

The production H0/H1/H2 engine, daily collector and public dashboard remain
unchanged.
