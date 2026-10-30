#!/usr/bin/env python3
"""
parse_metaexperiments.py - stage the Metaexperiment cell-density export for
plotting.

Metaexperiment logs are day-level records shared by every microscope that
ran that day (see the Trappy-Scopes framework docs) - not the same kind of
`experiment.yaml` as the per-scope run logs a cellcounting.py experiment
writes. Each one logs, per culture: a raw density reading (before
separation) and, when a separation step was run, a separator density
reading (after separation), via the `cell_counts` measurement stream
(`density`, `df`, `label`, `sep`). There is no mutant/strain field anywhere
in this stream, or in the log's top-level attribs - only the free-text
culture `label` - and the density values are already fully computed by the
logging framework, so nothing here is recomputed from raw counts.

Unlike the interim version of this script, this does not parse
`experiment.yaml` directly (and does not need `explorer.legacy.ExpExplorer`
or `trappy-explorer` at all): the source Metaexperiments live on the
instrument machine under the lab's `~/experiments/` archive, which is kept
strictly read-only and is not copied into this repo. Instead,
`data/metaexperiments/all_cell_counts.csv` is a periodic bulk export of that
archive's `cell_counts` stream (produced out-of-band, currently by hand -
see docs/metaexperiments.md for how and when it was last refreshed). This
script just validates and re-sorts that export into the same build/ contract
the rest of the pipeline expects.

If a fresher export needs the same read: every day-level Metaexperiment
whose folder name contains "metaexperiment" is loaded via
`explorer.legacy.ExpExplorer(dirs, extended_parse=True)`, and its
`cell_counts` rows are joined to their stream name via `measureid` alone -
`df_events` and `df` do not always agree on a log's own `eid` for the same
experiment, but `measureid` is unique across the whole corpus. An experiment
whose folder name matches but that turns out to carry no `cell_counts`
stream at all (an `MDev_*` per-scope run log can still contain the word
"metaexperiment" in its own descriptive title) contributes nothing and is
not an error. `experiment.yaml` files that are zero bytes fail to parse
entirely and must be skipped, not silently retried. A `cell_counts` row
whose `success` field is `None` (unconfirmed - almost none of them set it)
is still normally kept; one is only dropped when it's a duplicate reading
for the same label superseded by a later one that did compute a density
(see docs/metaexperiments.md for the one case this applied to).

`sep` is not a clean boolean in the raw source - it also shows up as the
literal strings "raw"/"sep"/"dillution", or missing entirely on every
reading before the `-31May26` culture cohort (nothing recorded, not
False). Naively doing `.astype(bool)` on that raw column silently mis-reads
it (every non-empty string, and NaN, becomes True; only bare None becomes
False) - so that normalization has to happen once, at export time, before
it lands in `all_cell_counts.csv` (see docs/metaexperiments.md for exactly
how each case was resolved). By the time this script reads the export,
`sep` is already a clean bool and `.astype(bool)` below is just a dtype
guarantee, not a conversion.

scaled_density, sample_media_ratio
------------------------------------
Two Metaexperiments merged in on 2026-09-22 (`675c564a1e`, 2026-09-14, and
`5b5ab9af8a`, 2026-09-21) are the first in this corpus whose raw
`cell_counts` export carries two fields no earlier reading has:
`scaled_density` and `sample_media_ratio`. Neither is defined anywhere in
the copies of `trappy-explorer`, `cellcounter`, or `cellcounting.py`
available when this was written, and both source files' framework code was
touched right around 2026-09-21 - so this looks like a genuinely new,
very recent field, not a parsing gap on this script's end. What's known
empirically: `sample_media_ratio` is blank on every reading seen so far;
`scaled_density` equals `density` exactly for both experiments' raw
(`sep = False`) reading, and is exactly 10x `density` for both experiments'
separator (`sep = True`) reading. Per Yatharth, both densities should be
shown rather than the pipeline picking one - see
tools/make_metaexperiment_plots.py for how. Every reading from before
2026-09-14 has no `scaled_density`/`sample_media_ratio` at all (the
framework didn't compute them yet), so those columns are simply blank
(NaN) on all 99 pre-existing rows in `all_cell_counts.csv` - not an
assumption that no correction applied, just genuinely not recorded.

Output (repo root, gitignored, rebuilt on every run):
    build/all_metaexperiment_counts.csv
        source_experiment, eid, label, dt, sep, density, df,
        scaled_density, sample_media_ratio
"""

import os

import pandas as pd

DATA_PATH = os.path.join("data", "metaexperiments", "all_cell_counts.csv")
BUILD_DIR = "build"
COLUMNS = ["source_experiment", "eid", "label", "dt", "sep", "density", "df",
           "scaled_density", "sample_media_ratio"]


def _ratio_text(value):
    """'(2, 18)' / '[2, 18]' / (2, 18) -> '2:18'; a bare number -> as is; blank -> NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")
    text = str(value).strip().strip("()[]")
    if not text:
        return float("nan")
    return ":".join(part.strip() for part in text.split(",")) if "," in text else text


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    out_path = os.path.join(BUILD_DIR, "all_metaexperiment_counts.csv")

    if not os.path.isfile(DATA_PATH) or os.path.getsize(DATA_PATH) == 0:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no export found at {DATA_PATH})")
        return

    df = pd.read_csv(DATA_PATH)

    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(
            f"{DATA_PATH} is missing expected column(s) {missing} - "
            f"has: {list(df.columns)}"
        )

    df["dt"] = pd.to_datetime(df["dt"])
    df["sep"] = df["sep"].astype(bool)
    df["label"] = df["label"].astype(str)
    # blank/NaN on every pre-2026-09-14 row - the framework didn't compute
    # these yet (see "scaled_density, sample_media_ratio" above), not a
    # conversion of anything already present.
    df["scaled_density"] = pd.to_numeric(df["scaled_density"], errors="coerce")
    # Since 2026-10-23 the logging script records sample_media_ratio as a
    # (sample, media) tuple, e.g. "(2, 18)" - a to_numeric() would silently
    # blank it. Keep it as "sample:media" text ("2:18"); empty stays empty.
    df["sample_media_ratio"] = df["sample_media_ratio"].apply(_ratio_text)

    out = df[COLUMNS].sort_values(["label", "dt", "sep"]).reset_index(drop=True)
    out.to_csv(out_path, index=False)

    n_labels = out["label"].nunique()
    n_exps = out["source_experiment"].nunique()
    n_scaled = out["scaled_density"].notna().sum()
    print(f"wrote {out_path} ({len(out)} rows, {n_labels} culture label(s), "
          f"{n_exps} Metaexperiment(s), {n_scaled} row(s) with a scaled_density)")


if __name__ == "__main__":
    main()
