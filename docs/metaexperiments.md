# Metaexperiments

A Metaexperiment log is a day-level record shared by every microscope that
ran that day — separate from a cellcounting.py experiment's own
`experiment.yaml` (see [Methodology](methodology.md)). Each day typically
logs, per culture: one **raw density** reading before separation, and,
when a separation step was run, one **separator density** reading after
separating — real calendar dates from day one, which is why this page plots
against actual date/time rather than elapsed hours.

There is no mutant/strain field in this stream, only the free-text culture
label (e.g. `Eptx18-5July26`), so this page can't join into the
[home page's](index.md) per-strain dashboard — it shows culture density and
separation efficiency instead. Most labels only appear on a single day; use
the filter box above the plot to isolate one or more cultures by label
instead of relying on a legend.

<iframe src="../plots/metaexperiments.html" width="100%" height="680" style="border:none;"
        title="Metaexperiment cultures"></iframe>

[Open full screen →](plots/metaexperiments.html){ .md-button }

## Where this data comes from

This is a bulk export of `data/metaexperiments/all_cell_counts.csv`, pulled
from every day-level Metaexperiment under the lab's `~/experiments/`
archive (identified by "metaexperiment" appearing in the experiment's
folder name) via `explorer.legacy.ExpExplorer`
(the [trappy-explorer](https://github.com/Trappy-Scopes/trappy-explorer)
package, `extended_parse=True`). `tools/parse_metaexperiments.py` no longer
parses `experiment.yaml` itself — the archive lives on the instrument
machine and is read strictly read-only, so nothing there is ever copied
into this repo; the script just validates and re-sorts the checked-in CSV.

The last export (September 2026) scanned 66 experiments whose folder name
matched "metaexperiment":

- 62 loaded; 4 had a zero-byte `experiment.yaml` and could not be parsed at
  all (all four dated 2025-11-13).
- Of the 62 loaded, one (`MDev_2025_01_16_tandh_calibration_metaexperiment_*`)
  turned out to be a per-scope run log whose own descriptive title happens
  to contain the word "metaexperiment" — it carries no `cell_counts` stream
  and correctly contributes no rows.
- 8 real day-level Metaexperiments declared a `cell_counts` stream but
  logged no actual measurements that day (nothing else recorded either, in
  most of them) — genuinely empty days, not a parsing gap.
- One `cell_counts` reading (`A3-24April26`, 2026-04-07 17:17:47) had no
  computed density; its `success` field reads `None` rather than an
  explicit `False` (like nearly every reading in this corpus, `success` is
  simply never confirmed either way), but a second reading for the same
  label 20 seconds later did compute a density, so the first is a
  superseded retake and was dropped from the export rather than kept as a
  blank.
- The result is 99 `cell_counts` rows across 53 contributing experiments
  and 64 distinct culture labels (Feb 2025 – Aug 2026).

One more thing worth knowing about the export as it stands: the label
`B-B raw` is reused across two unrelated early experiments
(2025-02-19 and 2025-02-20) rather than naming one culture.

Two more Metaexperiments were merged in on 2026-09-22:
`675c564a1e` (2026-09-14, culture `Kptx5-31Aug26`) and `5b5ab9af8a`
(2026-09-21, culture `31Aug26`) - 4 rows in total, bringing the export to
**103 rows, 55 experiments, 66 labels**. Each contributed a raw + separator
pair except `675c564a1e`, whose export had a third, leading row with every
payload field blank (`counts`, `density`, `label`, `sep` all empty) - a
stream-open marker rather than a real reading, dropped the same way other
placeholder rows are.

### scaled_density

Both of these two experiments' raw exports carry a field no earlier
reading has: `scaled_density`, alongside a `sample_media_ratio` that's
blank on every row seen so far. Neither is defined anywhere in the copies
of `trappy-explorer`, `cellcounter`, or `cellcounting.py` available when
this was written - and notably, `cellcounter/counter.py`,
`cellcounter/loader.py` and `cellcounting.py` were all touched right
around 2026-09-21 on the instrument machine, so this reads as a genuinely
new framework field, not a gap in what this repo's tooling parses. What's
known empirically, from these 4 rows: `scaled_density` equals `density`
exactly for each experiment's raw (`sep = False`) reading, and is exactly
10x `density` for each experiment's separator (`sep = True`) reading.

Per Yatharth: show both rather than picking one. The Metaexperiments plot
draws a hollow triangle at `scaled_density` alongside the usual circle/
square wherever a row has one and it differs from `density` - see
tools/make_metaexperiment_plots.py. All 99 rows from before 2026-09-14
have no `scaled_density` at all (not "assumed equal to density" - simply
never recorded), so nothing changes for them.

`sep` (raw vs. separator density) is not a clean boolean in the source
data — reviewed and normalized as follows:

- Every reading before the `-31May26` culture cohort (39 rows, 2025-02-18
  through 2026-04-09 — the entire archive prior to that point) has no
  `sep` value logged at all; the field wasn't in use yet. These are
  treated as raw (`sep = False`), on review.
- From the first `-31May26` reading (2026-06-22) on, `sep` is logged
  properly — as the literal strings `"raw"`/`"sep"` on that first day,
  then as a real boolean from the next day forward, with two later
  one-off exceptions: a `dillution` string (2026-08-25, `Gptx9-4Aug26`,
  mapped to `sep = True` as a post-dilution/separator-equivalent reading)
  and one more unlogged reading (2026-07-03, `Bptx13-31May26`, likewise
  treated as raw).

Refreshing this export means either re-running the same full scan against
the `~/experiments/` archive and replacing
`data/metaexperiments/all_cell_counts.csv` wholesale, or - as with the two
Metaexperiments merged in on 2026-09-22 - hand-merging a small, individually
exported `cell_counts` stream dump (dropped straight into
`data/metaexperiments/` as its own `*_cell_counts.csv` file) into the
existing export. Either way, `tools/parse_metaexperiments.py` itself needs
no changes to pick up a refreshed file - it only reads
`all_cell_counts.csv`, never the individual per-experiment dumps directly.
