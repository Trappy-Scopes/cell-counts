# cell-counts

Cell density measurements for the Trappy-Scopes lab, and the growth-curve
analysis built on top of them: dilution-compensated density, fitted growth
rate, doubling time, and — for colonies that get media added repeatedly —
segment-wise rates across each dilution.

## What is here

| | |
|---|---|
| Experiments | 1 |
| Colonies | 5 |
| Mutant | CC2894 |
| Span | 2026-08-18 to 2026-08-21 |
| Growth rate | 0.070 – 0.072 / hr |
| Doubling time | 9.6 – 10.0 hours |

## Growth curves

![Growth curves overview](plots/growth_curves_overview.png)

Every colony currently on record, dilution-compensated so that media
additions read as continuations of the same exponential rather than sudden
drops. [See the interactive version →](growth-curves.md)

## How an experiment gets here

1. Open an experiment with `create_exp(...)` (wraps `Experiment.Construct`).
2. Log every count with `new_count(name, *counts, df=..., mutant=..., ...)`,
   and every media addition with
   `log_media_addition(name, volume_before_ml, media_added_ml, ...)`. Both
   take a `date_override` / `time_override` for backfilling records after
   the fact.
3. Run `fit_curve()` and `analyse_growth()` — they populate the
   experiment's `analysis/` folder with the CSVs and figures this site
   reads.
4. Copy (or leave) the experiment folder under `data/<experiment-name>/`,
   commit, and push.

Everything on this site regenerates itself from `data/` on every push —
nothing above needs to be run again by hand. See [The data](data.md) for
the repository layout and exactly what `tools/parse_data.py` and
`tools/make_plots.py` do with it, and [Methodology](methodology.md) for
what "dilution-compensated" and "growth rate" actually mean.

## Before this framework

Counts used to be entered into per-file CSV templates and processed by a
fixed set of scripts. That pipeline — and the counts it recorded — is kept
in `legacy/` (and the `legacy` branch) for reference; see
`legacy/README.md`.

---

*`cellcounting.py`, the analysis it runs, and this site were built by
Claude, reviewed by Yatharth Bhasin.*
