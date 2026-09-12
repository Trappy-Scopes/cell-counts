#!/usr/bin/env python3
"""
parse_metaexperiments.py - extract cell-density readings from Metaexperiment
day-logs under data/metaexperiments/*/experiment.yaml.

A Metaexperiment log is a day-level record shared by every microscope that
ran that day (see the Trappy-Scopes framework docs) - not the same kind of
`experiment.yaml` as the per-scope run logs a cellcounting.py experiment
writes. Each one currently logs, per culture: one raw density reading
(before separation) and one separator density reading (after separation),
via the `cell_counts` measurement stream (`density`, `df`, `label`, `sep`).
There is no mutant/strain field anywhere in this stream, or in the log's
top-level attribs - only the free-text culture `label` - and the density
values are already fully computed by the logging framework, so this script
reads them as-is rather than recomputing anything from raw counts.

This is an interim, manual step: for now these folders are created by
copying just the `experiment.yaml` out of a real Metaexperiment_*/ folder
into data/metaexperiments/<name>/. Once a real exporter writes finished
density readings straight to data/, this script's glob pattern still holds
and it should need no changes; only the copying step goes away.

Reading goes through explorer.legacy.ExpExplorer (extended_parse=True) -
see the `trappy-explorer` package - never a hand-rolled YAML parse. That is
optional at build time (like bokeh already is for tools/make_plots.py): if
it isn't installed, this script prints why and writes an empty output
rather than failing the whole site build.

One join quirk found in the two example logs, worth documenting rather than
silently working around: `df_events` (the notes/streams) and `df` (the
results) don't always agree on this log's own `eid` for the same
experiment - a `measurement_stream` event for "cell_counts" can carry a
different eid than the result rows that stream produced. `measureid` is
unique across the whole corpus though (never reused between experiments in
practice), so the stream-name join here is on `measureid` alone, not
`(eid, measureid)`.

Output (repo root, gitignored, rebuilt on every run):
    build/all_metaexperiment_counts.csv
        source_folder, eid, label, dt, sep, density, df
"""

import glob
import os

import pandas as pd

DATA_DIR = os.path.join("data", "metaexperiments")
BUILD_DIR = "build"


def _experiment_dirs():
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        os.path.dirname(p)
        for p in glob.glob(os.path.join(DATA_DIR, "*", "experiment.yaml"))
    )


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    out_path = os.path.join(BUILD_DIR, "all_metaexperiment_counts.csv")

    dirs = _experiment_dirs()
    if not dirs:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no Metaexperiment folders found under {DATA_DIR}/)")
        return

    try:
        from explorer.legacy import ExpExplorer
    except ImportError:
        open(out_path, "w").close()
        print(
            "trappy-explorer not installed - skipping Metaexperiment parsing "
            f"({len(dirs)} folder(s) found but unread). "
            "pip install git+https://github.com/Trappy-Scopes/trappy-explorer.git"
        )
        return

    exp = ExpExplorer(dirs, extended_parse=True)
    results = exp.df.copy()
    events = exp.df_events.copy()

    if results.empty:
        open(out_path, "w").close()
        print(f"wrote {out_path} (0 experiments loaded any results)")
        return

    streams = (
        events[events["type"] == "measurement_stream"][["measureid", "name"]]
        .drop_duplicates()
    )
    joined = results.merge(streams, on="measureid", how="left")

    cc = joined[joined["name"] == "cell_counts"].copy()
    if cc.empty:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no cell_counts stream rows in {len(dirs)} folder(s))")
        return

    # source_folder identifies the row by what's actually on disk, independent
    # of the log's own (occasionally inconsistent) eid - see module docstring.
    # Read each folder alone and take the eid(s) that actually appear in its
    # *results* (df), not exp.data's key - those two can disagree (the July
    # folder's events use eid 432ee2bd48, but its result rows are logged
    # under 94151c6b30).
    dir_by_eid = {}
    for d in dirs:
        try:
            sub = ExpExplorer([d], extended_parse=False)
            eids_seen = set(sub.data.keys()) | set(sub.df["eid"].unique() if not sub.df.empty else [])
            for eid in eids_seen:
                dir_by_eid[eid] = os.path.basename(d)
        except Exception as exc:
            print(f"  {d}: could not re-check eid ({exc})")

    cc["source_folder"] = cc["eid"].map(dir_by_eid).fillna("(unknown)")
    cc["dt"] = pd.to_datetime(cc["dt"])
    cc["sep"] = cc["sep"].astype(bool)

    out = cc[["source_folder", "eid", "label", "dt", "sep", "density", "df"]].sort_values(
        ["label", "dt", "sep"]
    ).reset_index(drop=True)

    out.to_csv(out_path, index=False)
    n_labels = out["label"].nunique()
    n_exps = out["source_folder"].nunique()
    print(f"wrote {out_path} ({len(out)} rows, {n_labels} culture label(s), "
          f"{n_exps} Metaexperiment folder(s) of {len(dirs)} found)")


if __name__ == "__main__":
    main()
