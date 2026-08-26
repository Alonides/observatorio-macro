# Debt and NOK Regime Model v0.4.1

## Purpose

This branch is an experimental, reproducible overlay on the production
observatory. It separates five phenomena that are often collapsed into one
narrative:

- **URP** — short US sovereign-rejection pulse;
- **URR** — persistence into US discrimination or a rejection regime;
- **DSS** — international dollar shortage;
- **NKS** — stress specific to NOK;
- **NRS** — a possible Norwegian reversal after a NOK shock.

The production H0/H1/H2 engine, daily collector and public dashboard remain
unchanged.

## v0.4 correction: fresh risk-off onset

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

After this correction, URP produced one episode above 50 in the first complete
run: 11-16 April 2025, four sessions, peak about 59. URR classified it as a
pulse rather than a persistent rejection regime. Lehman 2008, the 2011 US
downgrade, the 2013 taper tantrum, Q4 2018, Covid 2020, the 2022 inflation
shock and the 2023 banking stress produced no URP episode above 50. DSS
separately detected the dollar shortages of 2008 and 2020.

## v0.4.1: walk-forward NOK residual

A raw NOK score based only on EUR/NOK and NOK/SEK overstates the number of
idiosyncratic Norwegian events. v0.4.1 therefore estimates the part of EUR/NOK
that is not normally explained by:

- EUR/SEK daily log returns;
- Brent daily log returns;
- VIX daily log returns.

The model is a robust Huber regression with:

- 504-session minimum training sample;
- 756-session maximum rolling sample;
- refit every five common market sessions;
- 20-session cumulative residual;
- robust median/MAD z-score using 252-756 prior cumulative residuals.

The process is strictly causal. Coefficients for session `t` use only sessions
before `t`, and the z-score at `t` is standardised only on cumulative residuals
before `t`. Future observations cannot revise a past score.

Positive residual z means NOK weakened more than the model expected; negative
z means it strengthened more than expected. A low residual does not prove that
there is no Norwegian stress. It means only that this particular anomaly
signal did not activate.

## Norwegian funding data

The short HTML table previously provided only about 100 Norway 10-year yield
observations. v0.4.1 requests the full official Norges Bank SDMX series:

`GOVT_GENERIC_RATES/B.10Y.GBON.`

This permits Norway-Bund funding stress to participate in NKS and NRS over a
substantially longer history. NIBOR-OIS remains optional until a stable,
homogeneous historical construction is frozen; missing NIBOR-OIS is never
converted into zero.

## Backtest design

The default fetch begins in 2003. Those three pre-history years allow residual
training and standardisation before the principal 2006-present evaluation
window. Outputs include:

- continuous URP, URR, DSS, NKS and NRS histories;
- episodes and annual alert-session counts;
- event windows for 2008, the 2014-15 oil shock, Covid 2020, 2022, the 2023
  banking episode and April 2025;
- residual coverage and latest coefficient diagnostics;
- synthetic falsification cases.

## Repository layout

- `src/observatorio/debt_nok_v04/residual.py`
- `src/observatorio/debt_nok_v04/regime.py`
- `src/observatorio/debt_nok_v04/backtest.py`
- `src/observatorio/debt_nok_v04/history.py`
- `scripts/backtest_regimes_v04.py`
- `tests/test_debt_nok_v04.py`
- `.github/workflows/backtest_v04.yml`

The branch remains experimental until the new full-history CI run is reviewed
and the NKS/NRS false-alert rate is accepted.
