# Legacy data

Counts kept by hand in per-file CSVs before this repo adopted the
Trappy-Scopes framework — heterogeneous in format, normalised here into one
schema (`tools/parse_legacy.py`) so they plot the same way as everything
else. This page is pure growth curves only — see `legacy/README.md` for
the original pipeline these came from, and below for what that excludes.

<iframe src="../plots/legacy.html" width="100%" height="620" style="border:none;"
        title="Legacy data explorer"></iframe>

[Open full screen →](plots/legacy.html){ .md-button }

## What's excluded, and why

**Motility/swimming assays** — a handful of legacy files record the
fraction of cells swimming (`*_swimmers` / `*_total` columns), not density
— `10pow4exp1.csv`, `10pow4exp2.csv`,
`resuspension_deflaggalation_assay_exp1.csv`. That's a different
measurement entirely; this parser only ever reads density columns and
never looks at the swimming ones, so these files simply have none of the
columns it needs and are skipped rather than force-fit into a density plot.

**Centrifugation and counting-protocol runs** — per Yatharth, this page is
pure growth curves only, so a few files that do have the right density
columns are excluded outright rather than merely kept-but-not-fit:
`raw_exports/centrifugation_10pow4_RepAB_Controls.csv` (a ~1-hour
centrifugation/recovery protocol test, not a growth curve) and
`ProtocolGrowthCurve_Exp1_F13Xseries.csv` plus the small `raw_exports/YB_*.csv`
files (counting-protocol development runs — testing the counting method
itself, e.g. ethanol-fixation volume, not a strain/mutant comparison). See
`EXCLUDED_FILES` in `tools/parse_legacy.py` for the exact list and reasons.
That leaves `TheEight.csv` as the only legacy growth curve in this corpus:
four genotypes (CC125, MBO2, ODA1, TPG1) tracked over about 11 days.

**Placeholder rows** — a few early rows in `TheEight.csv` are marked "Faux
Count" with all-zero counts, from before that assay actually started.
Dropped everywhere.

**Three large instrument exports** (`raw_exports/coimbra.csv`, `october24.csv`,
`september24.csv`, ~33 MB each) aren't tracked in git at all (see
`.gitignore`) and use a third, incompatible column schema besides — they're
out of scope for this parser for now.

## Mutant, media, condition

A growth curve here is defined by which mutant/strain it is (the `strain`
column), which media it was grown in, and optionally some other condition
(a perturbation like lights off — reserved for the future; nothing in this
corpus sets it yet). None of the surviving files record media explicitly,
so every row defaults to `media = "TAP"`, per Yatharth's "assume TAP
wherever not mentioned" rule, unless a future file adds its own `media`
column.

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
