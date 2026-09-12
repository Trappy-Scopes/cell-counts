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
That leaves `TheEight.csv` and `raw_exports/coimbra_growth_curves.csv` (see
below) as the legacy growth curves in this corpus: `TheEight.csv` has four
genotypes (CC125, MBO2, ODA1, TPG1) tracked over about 11 days, all in TAP.

**Placeholder rows** — a few early rows in `TheEight.csv` are marked "Faux
Count" with all-zero counts, from before that assay actually started.
Dropped everywhere.

**Two large instrument exports** (`raw_exports/october24.csv`,
`september24.csv`, ~33 MB each) aren't tracked in git at all (see
`.gitignore`) and use a third, incompatible column schema besides — they're
out of scope for this parser for now. A third, `raw_exports/coimbra.csv`,
turned out to hold real data worth keeping — see the next section.

## BG-11 media, from `coimbra.csv`

`raw_exports/coimbra.csv` is another of the large, gitignored instrument
exports above, but of its ~1M rows only 35 have anything in `strain` at
all (the rest is empty spreadsheet padding). 30 of those 35 are a real,
dated BG-11-vs-TAP comparison — three strains, each grown in both media,
sampled at 19/09 18:00 and again four times on 20/09. Per Yatharth, the
numeric strain codes in the original map to real strain names: `77` →
**CC2377**, `125` → **CC125**, `84` → **CC2894**. The remaining 5 rows
(`CC125-TAP`, `CC125-BG11-t0`/`-t15m`/`-fix`, `CC125-mytube`) have no date
recorded and are a separate single-snapshot protocol check, not a growth
curve — left out entirely, same reasoning as the exclusions above.

Rather than commit the 33 MB original, those 30 rows are extracted once
into a small, git-tracked file — `raw_exports/coimbra_growth_curves.csv` —
which `tools/parse_legacy.py` parses directly (see `_parse_coimbra_growth`);
`coimbra.csv` itself stays out of git and unparsed.

**A caveat worth knowing before reading this data**: every strain/media
condition has a reading at 19/09 18:00, then a reading roughly 60× lower
at 20/09 08:00 with nothing recorded in between — almost certainly an
unrecorded dilution or passage step, not real die-off. It's called out
row-by-row in the extract's own `comments` column. One consequence: a
doubling time fit across that gap isn't biologically meaningful, and in
practice comes out negative/infinite for every one of these six
conditions — so none of them currently produce a bar on the doubling-time
chart above; you'll only see this data on the real-time growth chart on
the home page.

## Mutant, media, condition

A growth curve here is defined by which mutant/strain it is (the `strain`
column), which media it was grown in, and optionally some other condition
(a perturbation like lights off — reserved for the future; nothing in this
corpus sets it yet). Only `raw_exports/coimbra_growth_curves.csv` records
its own media (BG-11 or TAP, see above); every other surviving file
defaults to `media = "TAP"`, per Yatharth's "assume TAP wherever not
mentioned" rule, since none of them record it explicitly.

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

`raw_exports/coimbra_growth_curves.csv` is the one exception: its density
was already computed in the original instrument export by a different
formula (`avg_count × dilution factor × 10,000`), so its rows carry that
value straight through rather than being recomputed by the formula above.
