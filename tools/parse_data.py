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

Treated cultures (a non-blank, non-vehicle `condition`, e.g. "10uM DCMU") are
kept out of their strain's group: `mutant` becomes e.g. "CC125 + 10uM DCMU" in
cell_counts and growth_summary, with the logged strain in `mutant_raw`.

Counts listed in data/suppress.csv are dropped here, from all three outputs
(see tools/suppress.py); build/suppressed_cellcounting.csv records what and why.

Outputs, at the repo root under build/ (gitignored; rebuilt by CI on every
push, never committed):
    build/all_cell_counts.csv
    build/all_media_additions.csv
    build/all_growth_summary.csv

Standard library + pandas. Run from the repo root.
"""

import os
import re

import pandas as pd

import suppress

DATA_DIR = "data"
BUILD_DIR = "build"

# A culture counted under a *treatment* (the per-count `condition` from
# cellcounting.new_count, e.g. "10uM DCMU", "1uM cyclohexamine") is not
# comparable to an untreated culture of the same strain, so in the build/ CSVs
# its `mutant` becomes "<mutant> + <treatment>" (e.g. "CC125 + 10uM DCMU").
# Every downstream plot then colours, filters and groups it separately
# instead of pooling an inhibited culture into the strain's growth rates.
# The strain as logged is kept in `mutant_raw`. A colony counts as treated if
# ANY of its counts had a treatment, even if it was later released.
#
# Not treatments: blank, "(none)", and vehicle controls - a condition with a
# standalone "VC" / "vehicle" / "control" word, e.g. "EtOH-VC".
VEHICLE_WORDS = {"vc", "vehicle", "control", "ctrl", "none"}


def _is_treatment(condition):
    text = str(condition).strip()
    if not text or text.lower() in ("nan", "none", "(none)"):
        return False
    words = {w for w in re.split(r"[^a-z0-9]+", text.lower()) if w}
    return not (words & VEHICLE_WORDS)


def _treatment(conditions):
    """'10uM DCMU' (or 'A + B' in first-seen order) from per-count condition
    strings or a growth_summary history ('(none) -> 10uM DCMU -> (none)'),
    else None. Vehicle controls and blanks are ignored."""
    found = []
    for value in pd.Series(conditions).dropna().astype(str):
        for part in value.split("->"):
            part = part.strip()
            if _is_treatment(part) and part not in found:
                found.append(part)
    return " + ".join(found) or None


def _group_treated(frame, treatment_of_label):
    """Add mutant_raw and re-label `mutant` for treated colonies."""
    frame["mutant_raw"] = frame["mutant"]
    for label, treatment in treatment_of_label.items():
        if treatment:
            rows = (frame["label"] == label) & frame["mutant"].notna()
            frame.loc[rows, "mutant"] = frame.loc[rows, "mutant"].astype(str) + " + " + treatment


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
    rules = suppress.load_rules("cellcounting")      # data/suppress.csv

    for name, path in _experiment_dirs():
        eid = _experiment_id(path, name)
        analysis = os.path.join(path, "analysis")

        cc = _read_csv(os.path.join(analysis, "cell_counts.csv"))
        cc = suppress.apply(cc, name, rules, "cellcounting", whole_if_empty=True)
        if cc is not None and cc.empty:
            cc = None
        if cc is not None:
            cc = cc.copy()
            cc["timestamp"] = pd.to_datetime(cc["timestamp"])
            if "mutant" in cc.columns:
                treated = ({lab: _treatment(g["condition"]) for lab, g in cc.groupby("label")}
                           if "condition" in cc.columns else {})   # older experiments: no condition column
                _group_treated(cc, treated)
            cc["experiment_id"] = eid
            cc["experiment_name"] = name
            cc["experiment_start"] = cc["timestamp"].min()
            # elapsed hours since each colony's own first reading
            cc["elapsed_hours"] = cc.groupby("label")["timestamp"].transform(
                lambda s: (s - s.min()).dt.total_seconds() / 3600.0
            )
            cell_counts.append(cc)

        ma = _read_csv(os.path.join(analysis, "media_additions.csv"))
        ma = suppress.apply(ma, name, rules, "cellcounting")
        if ma is not None and ma.empty:
            ma = None
        if ma is not None:
            ma = ma.copy()
            ma["timestamp"] = pd.to_datetime(ma["timestamp"])
            ma["experiment_id"] = eid
            ma["experiment_name"] = name
            media_additions.append(ma)

        gs = _read_csv(os.path.join(analysis, "growth_summary.csv"))
        gs = suppress.apply(gs, name, rules, "cellcounting")
        if gs is not None and gs.empty:
            gs = None
        if gs is not None:
            gs = gs.copy()
            if "mutant" in gs.columns:
                _group_treated(gs, {r.label: _treatment([r.condition]) for r in gs.itertuples()}
                               if "condition" in gs.columns else {})
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

    suppress.write_report("cellcounting")
    n = len(_experiment_dirs())
    print(f"{n} experiment folder(s) under {DATA_DIR}/")


if __name__ == "__main__":
    main()
