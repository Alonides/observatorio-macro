# Debt and NOK Regime Model v0.3

## Status

This is an experimental companion to the existing H0/H1/H2 observatory. It is
not wired into the public dashboard and does not replace the current engine.
The specification is frozen before the continuous historical test so that the
thresholds cannot be changed after observing the test period.

## Five separate outputs

1. **URP - US Rejection Pulse**: ten-session event in which the US 30-year
   yield rises, the broad dollar falls, and markets are in risk-off mode.
2. **URR - US Rejection Regime**: persistence of URP with relative US/Bund,
   dollar, gold and real-yield confirmation.
3. **DSS - Dollar Shortage Stress**: broad dollar appreciation under market
   stress, classified according to whether Treasuries rally or dislocate.
4. **NKS - NOK Stress**: EUR/NOK, NOK/SEK, Norway/Bund and optional residual or
   NIBOR-OIS stress.
5. **NRS - Norwegian Reversal Signal**: recovery of NOK against both EUR and
   SEK after a prior NKS shock, while Brent and Norway/Bund remain supportive.

A single composite number is deliberately not used as the primary output.
The same market can show high global stress and low US rejection at once.

## Locked windows

- 10 sessions: primary pulse.
- 20 sessions: confirmation.
- 60 sessions: persistence and reversal context.
- Five-session changes may later be displayed as acceleration, but cannot
  activate a regime by themselves.

The implementation never takes the maximum over several windows to select the
most favourable retrospective story.

## Core gates

URP requires all of the following over ten sessions:

- US 30-year yield: at least +20 basis points;
- broad dollar: at least -1 percent;
- either S&P 500 at most -3 percent or VIX at least 25.

Without at least +10 basis points of widening in US 10-year minus Bund 10-year,
URP is capped below 60.

URR requires persistence. A full rejection regime additionally requires a
persistent dollar fall and gold rising while the US real yield rises.

DSS is separate: it requires broad-dollar appreciation of at least +2 percent
in ten sessions or +4 percent in twenty sessions, together with VIX at least
25. A Treasury rally is labelled traditional safe haven; a yield rise is
labelled dollar shortage with Treasury dislocation.

## NOK rules

EUR/NOK is the primary exchange-rate variable. NOK/SEK controls for a broad
Scandinavian move. USD/NOK is excluded from the NRS gate because a falling
USD/NOK can be caused entirely by a weaker dollar.

NKS uses the available components and renormalises the declared weights. It
reports coverage; missing residual or funding data are never silently scored as
zero.

NRS has three states:

- inactive;
- candidate, when observable market gates pass but the residual is absent;
- confirmed, only when the rolling NOK residual is also negative enough.

## Reproducibility

Run unit and synthetic tests:

```bash
python -m unittest discover -s tests -v
python scripts/backtest_regimes.py --synthetic-only
```

Fetch long histories and run the continuous backtest:

```bash
python scripts/backtest_regimes.py --fetch --start 2006-01-01
```

The manual GitHub Action `Debt and NOK backtest` performs the same operation and
uploads `data/backtest_series.json` and `data/regime_backtest.json` as an
artifact.

## Current limitations

- The daily repository archive keeps about 900 observations and is not enough
  for a 2006-present test; the historical loader is therefore separate.
- The robust three-year NOK residual is not yet produced. NRS cannot be marked
  confirmed without it.
- NIBOR-OIS, Treasury auction quality, TIC holdings and cross-currency basis are
  optional future confirmation series.
- Norges Bank generic 10-year history may begin later than 2006. The loader
  reports actual coverage and never backfills invented values.
- Historical network ingestion must be run in an environment with internet
  access. Unit and synthetic tests are fully offline.

## Files

- `src/observatorio/regime.py`: frozen classifier and gates.
- `src/observatorio/backtest.py`: continuous session-by-session test.
- `src/observatorio/history.py`: official long-history adapters.
- `src/observatorio/scenarios.py`: synthetic falsification suite.
- `scripts/backtest_regimes.py`: command-line runner.
- `tests/test_regime.py` and `tests/test_backtest.py`: regression tests.
