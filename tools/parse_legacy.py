#!/usr/bin/env python3
"""
parse_legacy.py - normalise the pre-framework CSVs under legacy/data/ into one
tidy, repo-wide schema for tools/make_plots.py.

Why this exists
----------------
Before this repo adopted the Trappy-Scopes framework, counts were entered by
hand into copies of legacy/templates/template1.csv. Those files are
heterogeneous in ways that matter:

  * delimiter varies per file (";", ",", or tab), and a couple carry a UTF-8
    BOM on the header's first column.
  * some files also carry motility/swimming-assay columns
    (*_swimmers, *_total) bolted onto the same rows - a different measurement
    entirely (fraction of cells swimming, not density). This script only ever
    reads the density columns (count1..4, date, time, strain, inv_dil, ...)
    and never looks at the swimming columns, so motility data is simply never
    extracted - not filtered out after the fact, just never read.
  * a handful of files are *purely* motility assays (10pow4exp1/2.csv,
    resuspension_deflaggalation_assay_exp1.csv) and have none of the density
    columns at all. They are skipped automatically because they fail the
    "has the required density columns" check below - no special-casing
    needed.
  * a few rows are explicit placeholders - comments contain "Faux Count", or
    every count is zero with no dilution recorded - from before a real assay
    started. These are dropped.
  * three raw instrument exports (raw_exports/coimbra.csv, october24.csv,
    september24.csv) are tens of MB, are not tracked in git
    (see .gitignore), and use a third, incompatible schema entirely
    (strain, df, count1..5, density_per_mL, ...). They are not covered here;
    if you want them included, they need converting to template1 first (or
    this script needs a third branch) and, being large, probably Git LFS or
    a release asset rather than a plain commit.

Cell density - unchanged from the original pipeline
----------------------------------------------------
This reproduces legacy/script/analysis.py's normalize_cells_per_ml() exactly:

    avg_count       = mean(count1..4), ignoring blanks
    count_norm      = avg_count * (v_sample_ul + v_etoh_ul) / v_sample_ul
    density         = count_norm / HCM_CONSTANTS["total_vol_ml"]

`inv_dil` is read and carried through in the output (it's a real column in
the source files) but is *not* multiplied into `density` - an earlier
version of this script did that, on the assumption that `inv_dil` was a
counting dilution the original pipeline had forgotten to apply. That
assumption was wrong, per Yatharth - reverted, so these numbers match
whatever the old pipeline would have reported for the same files.

Output (repo root, gitignored, rebuilt on every run):
    build/all_legacy_counts.csv
        source_file, strain, label, date, time, timestamp, exp_time,
        time_units, avg_count, inv_dil, v_sample_ul, v_etoh_ul, density,
        comments

Standard library + pandas. Run from the repo root.
"""

import glob
import io
import os
import re

import numpy as np
import pandas as pd

LEGACY_DATA_DIR = os.path.join("legacy", "data")
BUILD_DIR = "build"

HCM_CONSTANTS = {"total_vol_ml": 0.00040}

REQUIRED_COLUMNS = {"count1", "count2", "count3", "count4", "date", "strain", "replicate"}

DELIMITERS = [";", ",", "\t"]


def _sniff_and_read(path):
    """Try each known delimiter; return (df, delimiter) for the one that
    actually produces the expected columns, or (None, None)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8-sig", errors="replace")  # strips BOM if present

    best = None
    for delim in DELIMITERS:
        try:
            df = pd.read_csv(io.StringIO(text), sep=delim, engine="python")
        except Exception:
            continue
        cols = {c.strip().lower() for c in df.columns}
        if REQUIRED_COLUMNS.issubset(cols):
            df.columns = [c.strip().lower() for c in df.columns]
            return df, delim
        if best is None or len(cols & REQUIRED_COLUMNS) > best[1]:
            best = (df, len(cols & REQUIRED_COLUMNS))
    return None, None


_DATE_FORMATS = ("%d/%m/%Y", "%d/%m/%y")


def _parse_timestamp(date_str, time_str):
    """dd/mm/yyyy or dd/mm/yy + HH:MM. Returns pd.NaT (not a raise) on
    anything else - e.g. the one malformed "27-Jun" (no year) row in
    centrifugation_10pow4_RepAB_Controls.csv - so the caller can drop and
    count it instead of the whole file blowing up."""
    date_str = str(date_str).strip()
    time_str = str(time_str).strip() if pd.notna(time_str) and str(time_str).strip() else "00:00"
    if re.fullmatch(r"\d{3,4}", time_str):
        # bare military time with no colon, e.g. "1350" -> "13:50", "930" -> "09:30"
        time_str = time_str.zfill(4)
        time_str = f"{time_str[:2]}:{time_str[2:]}"
    for fmt in _DATE_FORMATS:
        try:
            return pd.to_datetime(f"{date_str} {time_str}", format=f"{fmt} %H:%M")
        except ValueError:
            continue
    return pd.NaT


def _to_float(x):
    try:
        v = float(x)
        return v
    except (TypeError, ValueError):
        return np.nan


def _parse_file(path):
    df, delim = _sniff_and_read(path)
    if df is None:
        return None, "no delimiter produced the required density columns (not a template1-style file)"

    n_total = len(df)
    # time_units (and, in a couple of files, the date) is only written on the
    # first row of a block and left blank after that - a spreadsheet habit,
    # not a missing value - so forward-fill it in original row order before
    # anything gets dropped/reordered.
    if "time_units" in df.columns:
        df["time_units"] = df["time_units"].replace("", np.nan).ffill()

    comments = df["comments"].astype(str) if "comments" in df.columns else pd.Series([""] * n_total)
    is_faux = comments.str.contains("faux", case=False, na=False)

    counts = df[["count1", "count2", "count3", "count4"]].apply(pd.to_numeric, errors="coerce")
    avg_count = counts.mean(axis=1, skipna=True)

    all_zero_untagged = (counts.fillna(0).sum(axis=1) == 0) & df.get(
        "inv_dil", pd.Series([np.nan] * n_total)
    ).apply(_to_float).fillna(0).eq(0)

    drop_mask = is_faux | (avg_count.isna()) | all_zero_untagged
    n_dropped = int(drop_mask.sum())

    kept = df.loc[~drop_mask].copy()
    avg_count = avg_count.loc[~drop_mask]

    v_sample = kept.get("v_sample_ul", pd.Series(dtype=float)).apply(_to_float)
    v_etoh = kept.get("v_etoh_ul", pd.Series(dtype=float)).apply(_to_float)
    # inv_dil is carried through as a column (see module docstring) but is not
    # part of the density calculation - matches legacy/script/analysis.py.
    inv_dil = kept.get("inv_dil", pd.Series(dtype=float)).apply(_to_float)

    count_norm = avg_count * (v_sample + v_etoh) / v_sample
    density = count_norm / HCM_CONSTANTS["total_vol_ml"]

    timestamps = [
        _parse_timestamp(d, t)
        for d, t in zip(kept.get("date", pd.Series(dtype=str)), kept.get("time", pd.Series(dtype=str)))
    ]
    timestamps = pd.Series(timestamps, index=kept.index)
    n_bad_dates = int(timestamps.isna().sum())

    out = pd.DataFrame({
        "source_file": os.path.relpath(path, LEGACY_DATA_DIR),
        "strain": kept.get("strain", pd.Series(dtype=str)).astype(str).str.strip(),
        "label": kept.get("replicate", pd.Series(dtype=str)).astype(str).str.strip(),
        "date": kept.get("date"),
        "time": kept.get("time"),
        "timestamp": timestamps,
        "exp_time": kept.get("exp_time", pd.Series(dtype=float)).apply(_to_float),
        "time_units": kept.get("time_units", pd.Series([""] * len(kept))).astype(str),
        "avg_count": avg_count,
        "inv_dil": inv_dil,
        "v_sample_ul": v_sample,
        "v_etoh_ul": v_etoh,
        "density": density,
        "comments": kept.get("comments", pd.Series([""] * len(kept))).astype(str),
    })

    out = out.dropna(subset=["timestamp", "density"])
    n_no_ts_or_density = len(kept) - len(out) - 0  # informational only

    note = (
        f"{len(out)} usable row(s) kept, {n_dropped} dropped as placeholder/empty, "
        f"{n_bad_dates} dropped for an unparseable date"
    )
    return out, note


def _fit_growth_rate(sub, min_points=3):
    """Log-linear regression of density vs. elapsed hours since this group's
    own first reading - the same method tools/parse_data.py's growth_summary
    uses (see cellcounting.py's _fit_growth_rate), so legacy and current
    doubling times land on the same footing and can share one dashboard.
    Returns None below min_points, or if densities aren't all positive."""
    sub = sub.sort_values("timestamp")
    t0 = sub["timestamp"].iloc[0]
    hours = (sub["timestamp"] - t0).dt.total_seconds().to_numpy() / 3600.0
    density = sub["density"].to_numpy()

    if len(sub) < min_points or np.any(density <= 0):
        return None

    log_density = np.log(density)
    slope, intercept = np.polyfit(hours, log_density, 1)
    pred = slope * hours + intercept
    ss_res = np.sum((log_density - pred) ** 2)
    ss_tot = np.sum((log_density - log_density.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    growth_rate = slope
    doubling_time = np.log(2) / growth_rate if growth_rate > 0 else float("inf")
    return {
        "n_points": len(sub),
        "growth_rate_per_hr": growth_rate,
        "growth_rate_per_24hr": growth_rate * 24,
        "doubling_time_hr": doubling_time,
        "r_squared": r_squared,
    }


def _growth_summary(combined):
    """One row per (source_file, strain, label) with enough points to fit -
    the legacy-side counterpart of build/all_growth_summary.csv.

    Skips any group whose time_units reads "mins": a handful of files (e.g.
    centrifugation_10pow4_RepAB_Controls.csv) record density before/after a
    ~60-minute centrifugation or resuspension step, not a growth curve - a
    "doubling time" fit to 60 minutes of data is not a biologically
    meaningful number (cells do not double in 40 minutes) even though the
    regression happily produces one. Excluded from this fit, not from the
    legacy counts file - the raw points are still there to look at."""
    rows = []
    n_skipped_short = 0
    for (source_file, strain, label), sub in combined.groupby(["source_file", "strain", "label"]):
        units = sub["time_units"].astype(str).str.strip().str.lower()
        if (units == "mins").any():
            n_skipped_short += 1
            continue
        fit = _fit_growth_rate(sub)
        if fit is None:
            continue
        rows.append({"source_file": source_file, "strain": strain, "label": label, **fit})
    if n_skipped_short:
        print(f"  ({n_skipped_short} colony/replicate group(s) skipped for growth-rate fitting - "
              f"minute-scale assay, not a growth curve)")
    if not rows:
        return pd.DataFrame(columns=["source_file", "strain", "label", "n_points",
                                      "growth_rate_per_hr", "growth_rate_per_24hr",
                                      "doubling_time_hr", "r_squared"])
    return pd.DataFrame(rows)


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)

    paths = sorted(glob.glob(os.path.join(LEGACY_DATA_DIR, "*.csv"))) + sorted(
        glob.glob(os.path.join(LEGACY_DATA_DIR, "raw_exports", "*.csv"))
    )

    frames = []
    print(f"scanning {len(paths)} file(s) under {LEGACY_DATA_DIR}/")
    for path in paths:
        try:
            out, note = _parse_file(path)
        except Exception as exc:  # a malformed file must never take the rest down
            print(f"  {path}: SKIPPED ({exc})")
            continue
        rel = os.path.relpath(path, LEGACY_DATA_DIR)
        if out is None:
            print(f"  {rel}: skipped - {note}")
            continue
        if out.empty:
            print(f"  {rel}: 0 usable rows ({note}) - skipped")
            continue
        print(f"  {rel}: {note}")
        frames.append(out)

    out_path = os.path.join(BUILD_DIR, "all_legacy_counts.csv")
    if not frames:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no usable legacy rows found)")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["strain", "label", "timestamp"]).reset_index(drop=True)
    combined.to_csv(out_path, index=False)
    print(f"wrote {out_path} ({len(combined)} rows, {combined['strain'].nunique()} strain(s), "
          f"{combined['source_file'].nunique()} source file(s))")

    gs = _growth_summary(combined)
    gs_path = os.path.join(BUILD_DIR, "all_legacy_growth_summary.csv")
    gs.to_csv(gs_path, index=False)
    print(f"wrote {gs_path} ({len(gs)} colony/replicate fit(s) with >=3 points)")


if __name__ == "__main__":
    main()
