#!/usr/bin/env python3
"""
parse_data.py - aggregate every experiment under data/ into tidy, repo-wide
CSVs for tools/make_plots.py.

An "experiment" is any direct subdirectory of data/ that has an
analysis/cell_counts.csv - the file cellcounting.py writes on every fit.
Each experiment folder is produced by the Trappy-Scopes framework
(Experiment.Construct) and cellcounting.py's new_count / log_media_addition /
fit_curve / analyse_growth workflow; see the root README.md.

Per experiment, reads (when present):
    analysis/cell_counts.csv       label, mutant, df, density, timestamp,
                                    compensated_density, perturbed
    analysis/media_additions.csv   label, volume_before_ml, media_added_ml,
                                    dilution_fraction, timestamp
    analysis/growth_summary.csv    label, mutant, perturbed, n_points,
                                    growth_rate_per_hr, growth_rate_per_24hr,
                                    doubling_time_hr, r_squared

and tags every row with:
    experiment_id     the .experiment file's contents (a short hash), or the
                       folder name if there is no .experiment file
    experiment_name    the folder name under data/
    experiment_start   the earliest cell_counts timestamp for that experiment

cell_counts rows also get elapsed_hours: hours since that colony's own first
reading in that experiment, which is what every plot uses for its x-axis (not
a bare timestamp - experiments start on different dates).

Outputs, at the repo root under build/ (gitignored; rebuilt by CI on every
push, never committed):
    build/all_cell_counts.csv
    build/all_media_additions.csv
    build/all_growth_summary.csv

Standard library + pandas. Run from the repo root.
"""

import os

import pandas as pd

DATA_DIR = "data"
BUILD_DIR = "build"


def _experiment_dirs():
    """Every data/<name>/ that looks like a real experiment (has been
    fitted at least once, i.e. has analysis/cell_counts.csv)."""
    if not os.path.isdir(DATA_DIR):
        return []
    found = []
    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if not os.path.isdir(path):
            continue
        if os.path.isfile(os.path.join(path, "analysis", "cell_counts.csv")):
            found.append((name, path))
    return found


def _experiment_id(path, name):
    id_file = os.path.join(path, ".experiment")
    if os.path.isfile(id_file):
        with open(id_file) as fh:
            eid = fh.read().strip()
        if eid:
            return eid
    return name


def _read_csv(path):
    if not os.path.isfile(path):
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    return df


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)

    cell_counts, media_additions, growth_summary = [], [], []

    for name, path in _experiment_dirs():
        eid = _experiment_id(path, name)
        analysis = os.path.join(path, "analysis")

        cc = _read_csv(os.path.join(analysis, "cell_counts.csv"))
        if cc is not None:
            cc["timestamp"] = pd.to_datetime(cc["timestamp"])
            cc["experiment_id"] = eid
            cc["experiment_name"] = name
            cc["experiment_start"] = cc["timestamp"].min()
            # elapsed hours since each colony's own first reading
            cc["elapsed_hours"] = cc.groupby("label")["timestamp"].transform(
                lambda s: (s - s.min()).dt.total_seconds() / 3600.0
            )
            cell_counts.append(cc)

        ma = _read_csv(os.path.join(analysis, "media_additions.csv"))
        if ma is not None:
            ma["timestamp"] = pd.to_datetime(ma["timestamp"])
            ma["experiment_id"] = eid
            ma["experiment_name"] = name
            media_additions.append(ma)

        gs = _read_csv(os.path.join(analysis, "growth_summary.csv"))
        if gs is not None:
            gs["experiment_id"] = eid
            gs["experiment_name"] = name
            if cc is not None:
                gs["experiment_start"] = cc["timestamp"].min()
            growth_summary.append(gs)

    def _write(frames, filename):
        out_path = os.path.join(BUILD_DIR, filename)
        if not frames:
            # still write an empty file with no header so make_plots.py can
            # tell "ran, found nothing" apart from "never ran"
            open(out_path, "w").close()
            print(f"wrote {out_path} (no experiments found)")
            return
        pd.concat(frames, ignore_index=True).to_csv(out_path, index=False)
        print(f"wrote {out_path} ({sum(len(f) for f in frames)} rows)")

    _write(cell_counts, "all_cell_counts.csv")
    _write(media_additions, "all_media_additions.csv")
    _write(growth_summary, "all_growth_summary.csv")

    n = len(_experiment_dirs())
    print(f"{n} experiment folder(s) under {DATA_DIR}/")


if __name__ == "__main__":
    main()
