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

Refreshing this export means re-running the same scan against the
`~/experiments/` archive and replacing
`data/metaexperiments/all_cell_counts.csv`; `tools/parse_metaexperiments.py`
needs no changes to pick up a refreshed file.
