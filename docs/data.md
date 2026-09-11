# The data

## Repository layout

```
data/<experiment-name>/        one Trappy-Scopes experiment (Experiment.Construct)
  .experiment                  short experiment id
  experiment.yaml, logs.yaml,  framework bookkeeping
    sessions.yaml
  scripts/cellcounting.py      the exact script that ran this experiment
  analysis/                    written by fit_curve() / analyse_growth():
    cell_counts.csv              label, mutant, df, density, timestamp,
                                  compensated_density, perturbed
    media_additions.csv          label, volume_before_ml, media_added_ml,
                                  dilution_fraction, timestamp
    growth_summary.csv            one row per colony: fitted rate, doubling
                                  time, R²
    *.png                         per-colony and per-mutant figures

tools/parse_data.py            aggregates every data/*/analysis/*.csv into
tools/make_plots.py            build/all_*.csv, then builds plots/*.png and
                                plots/interactive.html from those

legacy/                         the pipeline this repo used before
                                cellcounting.py — see legacy/README.md
```

## Generated files

`build/` and `plots/interactive.html` are rebuilt from `data/` on every
push and are not tracked — see **How the site is built**, below.
`plots/*.png` (the two overview figures) *are* tracked, so they render
inline in the README and on this page even for someone browsing the repo
directly on GitHub rather than the published site; refresh them locally
(`python tools/parse_data.py && python tools/make_plots.py`) and commit
when you want that snapshot current. The live site at
[trappy-scopes.github.io/cell-counts](https://trappy-scopes.github.io/cell-counts)
is always fresh regardless, since it is rebuilt in CI on every push.

Each experiment's own `analysis/*.csv` and `*.png` **are** tracked — they
are cellcounting.py's primary output for that experiment, not a build
artifact of this site.

## How the site is built

`.github/workflows/pages.yml`, on every push touching `data/`, `tools/` or
`docs/`:

1. `tools/parse_data.py` — walks `data/*/analysis/`, writes
   `build/all_cell_counts.csv`, `build/all_media_additions.csv`,
   `build/all_growth_summary.csv`
2. `tools/make_plots.py` — writes `growth_curves_overview.png`,
   `doubling_time_summary.png` and `interactive.html` into `plots/`
3. copies `plots/` and every experiment's `analysis/*.png` into `docs/plots/`
4. `mkdocs gh-deploy` — publishes to the `gh-pages` branch

Nothing is committed back to `main`, so pushing here never conflicts with
a build — a person's next push never has to rebase over a bot commit.
The aggregated CSVs are also uploaded as a workflow artifact (`parsed-data`,
90-day retention) so the numbers behind the site are downloadable without
cloning.

## What is intentionally not tracked

`legacy/data/raw_exports/coimbra.csv`, `october24.csv` and `september24.csv`
are ~33 MB instrument dumps predating this framework. They are excluded via
`.gitignore` rather than committed — GitHub's per-file limit is 100 MB, and
a repo this size would make every clone noticeably slower for no benefit to
the current pipeline. If they need to be versioned, use Git LFS or attach
them as a release asset. See `legacy/README.md`.

`data/<experiment>/expstate.pickle` (framework runtime state) is also
excluded, via a blanket `*.pickle` rule — it isn't needed to reproduce
anything on this site and pickles are best not carried in git regardless.
