"""
suppress.py - keep chosen counts out of the published site without deleting them.

Some data belongs in the repo (the experiment's own notebook, its raw files) but
not in the aggregated site: a run with too few readings to fit, a failed culture,
a protocol test. List it in  data/suppress.csv  and the build step drops it from
every build/ CSV, so it appears in none of the plots, dashboards or doubling-time
charts. Nothing under data/ is modified or deleted.

data/suppress.csv columns (all matching is case-sensitive shell-style globbing):
    dataset     cellcounting | metaexperiment | *     which pipeline the rule is for
    experiment  folder name under data/ (cellcounting) or the Metaexperiment name
                (metaexperiment); wildcards allowed, e.g. MDev__ghost__2026_10_22*
    label       colony / culture label; * (or blank) = every colony of that experiment
    reason      free text - shown in the CI log and written to build/suppressed_<dataset>.csv

Lines starting with '#' are comments. To bring data back, delete or comment its line.

Every build writes build/suppressed_<dataset>.csv listing what was dropped and why, and
build/suppressed_experiments.txt (experiments that were suppressed *entirely*, so
the workflow can also skip copying their per-experiment figures into the site).
"""

import csv
import fnmatch
import os

RULES_PATH = os.path.join("data", "suppress.csv")
BUILD_DIR = "build"
_REPORT = []          # (dataset, experiment, label, rows, reason)
_WHOLE = set()        # experiments of the cellcounting dataset suppressed entirely


def load_rules(dataset, path=RULES_PATH):
    """Rules for one dataset ('cellcounting' or 'metaexperiment') as a list of
    (experiment_glob, label_glob, reason)."""
    if not os.path.isfile(path):
        return []
    rules = []
    with open(path, newline="") as fh:
        lines = (ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#"))
        for row in csv.DictReader(lines):
            if (row.get("dataset") or "*").strip() not in (dataset, "*"):
                continue
            experiment = (row.get("experiment") or "").strip()
            if not experiment:
                continue
            rules.append((experiment, (row.get("label") or "*").strip() or "*",
                          (row.get("reason") or "").strip()))
    return rules


def apply(df, experiment, rules, dataset, label_col="label", whole_if_empty=False):
    """Drop the rows of `df` (one experiment's frame) that a rule suppresses.
    Returns the filtered frame; the drop is recorded for write_report().
    whole_if_empty: pass True for the frame that defines the experiment (cell_counts), so
    an experiment with no rows left is listed in suppressed_experiments.txt."""
    if df is None or not rules:
        return df
    keep = [True] * len(df)
    for exp_glob, label_glob, reason in rules:
        if not fnmatch.fnmatchcase(experiment, exp_glob):
            continue
        hits = [bool(fnmatch.fnmatchcase(str(lb), label_glob)) for lb in df[label_col]]
        n = sum(1 for h, k in zip(hits, keep) if h and k)
        if n:
            _REPORT.append((dataset, experiment, label_glob, n, reason))
            print(f"  suppressed {n} row(s): {dataset} / {experiment} / {label_glob}"
                  f"{' - ' + reason if reason else ''}")
        keep = [k and not h for k, h in zip(keep, hits)]
    out = df[keep]
    if whole_if_empty and len(out) == 0 and len(df) > 0:
        _WHOLE.add(experiment)
    return out


def write_report(dataset):
    """Write build/suppressed_<dataset>.csv (and, for cellcounting,
    build/suppressed_experiments.txt)."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    with open(os.path.join(BUILD_DIR, f"suppressed_{dataset}.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "experiment", "label", "rows", "reason"])
        w.writerows(r for r in _REPORT if r[0] == dataset)
    if dataset == "cellcounting":
        with open(os.path.join(BUILD_DIR, "suppressed_experiments.txt"), "w") as fh:
            fh.write("".join(f"{name}\n" for name in sorted(_WHOLE)))
