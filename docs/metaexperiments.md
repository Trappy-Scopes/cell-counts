# Metaexperiments

A Metaexperiment log is a day-level record shared by every microscope that
ran that day — separate from a cellcounting.py experiment's own
`experiment.yaml` (see [Methodology](methodology.md)). Each day typically
logs, per culture: one **raw density** reading before separation, and one
**separator density** reading after separating — real calendar dates from
day one, which is why this page plots against actual date/time rather than
elapsed hours.

There is no mutant/strain field in this stream, only the free-text culture
label (e.g. `Eptx18-5July26`), so this page can't join into the
[home page's](index.md) per-strain dashboard — it shows culture density and
separation efficiency instead.

<iframe src="../plots/metaexperiments.html" width="100%" height="600" style="border:none;"
        title="Metaexperiment cultures"></iframe>

[Open full screen →](plots/metaexperiments.html){ .md-button }

## Where this data comes from, for now

This is parsed directly from `experiment.yaml` in each
`data/metaexperiments/<name>/` folder — copied in by hand for now, as a
worked example, ahead of a proper exporter that will write finished density
readings straight there. The parser (`tools/parse_metaexperiments.py`)
reads through `explorer.legacy.ExpExplorer`
(the [trappy-explorer](https://github.com/Trappy-Scopes/trappy-explorer)
package) and needs no changes when that exporter lands — it already just
globs `data/metaexperiments/*/experiment.yaml`.
