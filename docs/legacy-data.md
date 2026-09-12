# Legacy data

Counts kept by hand in per-file CSVs before this repo adopted the
Trappy-Scopes framework — heterogeneous in format, normalised here into one
schema (`tools/parse_legacy.py`) so they plot the same way as everything
else. See `legacy/README.md` for the original pipeline these came from.

<iframe src="../plots/legacy.html" width="100%" height="620" style="border:none;"
        title="Legacy data explorer"></iframe>

[Open full screen →](plots/legacy.html){ .md-button }

## What's excluded, and why

**Motility/swimming assays** — a handful of legacy files record the
fraction of cells swimming (`*_swimmers` / `*_total` columns), not density.
That's a different measurement entirely; this page and the doubling-time
dashboard on the [home page](index.md) never read those columns, so those
files simply contribute nothing rather than being force-fit into a density
plot.

**Minute-timescale protocol tests** — `centrifugation_10pow4_RepAB_Controls.csv`
records density before/after centrifugation and a wait under a light
source, over about an hour — a real, useful measurement, but not a growth
curve, so it's excluded from the doubling-time dashboard specifically
(fitting exponential growth to 60 minutes of data produces a number, just
not a biologically meaningful one). It's still plotted above.

**Placeholder rows** — a few early rows in `TheEight.csv` are marked "Faux
Count" with all-zero counts, from before that assay actually started.
Dropped everywhere.

**Three large instrument exports** (`raw_exports/coimbra.csv`, `october24.csv`,
`september24.csv`, ~33 MB each) aren't tracked in git at all (see
`.gitignore`) and use a third, incompatible column schema besides — they're
out of scope for this parser for now.

## Density formula

This site reproduces the original pipeline's (`legacy/script/analysis.py`)
`normalize_cells_per_ml()` exactly, so these numbers match whatever it would
have reported for the same files:

```
avg_count = mean(count1..4)
count_norm = avg_count × (v_sample_ul + v_etoh_ul) / v_sample_ul
density    = count_norm / 0.00040
```

`inv_dil` (the dilution a sample was prepared at before counting, recorded
as its reciprocal — 1000 means diluted 1:1000) is a real column in the
source files, but was never part of this formula: it appears once in
`legacy/script/analysis.py` as a documented dataclass field and is never
read again anywhere in that pipeline. It's dropped from
`build/all_legacy_counts.csv` entirely rather than carried through unused —
it's only read internally, as a signal for detecting placeholder rows.
