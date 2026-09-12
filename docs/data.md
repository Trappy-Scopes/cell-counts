# The data

Everything on this site is rebuilt from `data/` and `legacy/data/` on every
push — nothing here needs to be run again by hand.

```
data/<experiment-name>/        one cellcounting.py experiment (Experiment.Construct)
data/metaexperiments/          all_cell_counts.csv, a bulk export from ~/experiments (see Metaexperiments)
legacy/data/                   pre-framework CSVs (see Legacy data)

tools/parse_data.py            data/*/analysis/*.csv          -> build/all_*.csv
tools/parse_metaexperiments.py data/metaexperiments/*/         -> build/all_metaexperiment_counts.csv
tools/parse_legacy.py          legacy/data/**/*.csv            -> build/all_legacy_counts.csv,
                                                                   all_legacy_growth_summary.csv
tools/make_plots.py, make_metaexperiment_plots.py,
tools/make_legacy_plots.py, make_home_dashboard.py
                                -> plots/*.png, plots/*.html
```

`build/` and everything under `plots/` are gitignored and rebuilt by
[`.github/workflows/pages.yml`](https://github.com/Trappy-Scopes/cell-counts/blob/main/.github/workflows/pages.yml)
on every push touching `data/`, `legacy/data/`, `tools/`, `docs/` or
`mkdocs.yml`; the aggregated CSVs are also uploaded as a 90-day workflow
artifact. Each experiment's own `analysis/*.csv` and `*.png`, under
`data/<experiment>/`, **are** tracked — they're `cellcounting.py`'s primary
output, not a build artifact of this site.

See [Metaexperiments](metaexperiments.md#where-this-data-comes-from)
and [Legacy data](legacy-data.md#whats-excluded-and-why) for what those two
sources' parsers do and don't cover.
