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
    (strain, df, count1..5, density_per_mL, ...). october24.csv and
    september24.csv are not covered here - if you want them included, they
    need converting to template1 first (or another branch like the one
    below) and, being large, probably Git LFS or a release asset rather
    than a plain commit.

    coimbra.csv turned out to hold the only BG-11 data in this whole
    corpus (see "BG-11 media" below) - of its ~1M rows, only 35 have
    anything in `strain` at all (the rest is empty spreadsheet padding),
    and of those 35, 30 are a real dated BG-11-vs-TAP comparison. Rather
    than commit the 33MB original, those 30 rows are extracted once into
    a small, git-tracked file this script *does* read - see
    `raw_exports/coimbra_growth_curves.csv` and `_parse_coimbra_growth`
    below. coimbra.csv itself stays gitignored and unparsed.

Only pure growth curves, by explicit request
----------------------------------------------
Even among the files with the right density columns, a few are not growth
curves at all and are excluded outright (see EXCLUDED_FILES below), on top
of the motility-only files above that were already excluded for lacking
density columns in the first place:

  * raw_exports/centrifugation_10pow4_RepAB_Controls.csv - a ~1-hour
    centrifugation/recovery protocol test, not a growth curve (it was
    already excluded from _growth_summary's doubling-time fit for the same
    reason; now excluded from the counts file too, so it no longer shows up
    in the legacy plot either).
  * ProtocolGrowthCurve_Exp1_F13Xseries.csv, raw_exports/YB_E0.csv,
    YB_E4.csv, YB_E4noEtOH.csv, YB_E5noEtOH.csv, YB_N0.csv, YB_test.csv -
    counting-protocol development runs (validating the protocol itself -
    ethanol-fixation volume, dilution, etc. - not a strain/mutant
    comparison), not biological growth curves.

That leaves TheEight.csv (four genotypes - CC125, MBO2, ODA1, TPG1 - over
~11 days, all TAP) and raw_exports/coimbra_growth_curves.csv (three
genotypes - CC2377, CC125, CC2894 - each in BG-11 and TAP, over 2 days) as
the legacy growth curves in this corpus.

BG-11 media
------------
raw_exports/coimbra_growth_curves.csv is a curated, git-tracked extract of
the 30 real data rows buried in the much larger raw_exports/coimbra.csv
(see above). Per Yatharth: strain codes 77/125/84 in the original are
CC2377/CC125/CC2894, and only the dated rows are growth curves - 5 further
undated rows in the original (`CC125-TAP`, `CC125-BG11-t0/-t15m/-fix`,
`CC125-mytube`) are a separate, single-snapshot protocol check and were
left out of the extract entirely, same reasoning as EXCLUDED_FILES below.

This is the only place BG-11 appears anywhere in this corpus, and it comes
with a real caveat worth knowing before reading its numbers: every
strain/media condition has a reading at 19/09 18:00, then a ~60x lower
reading at 20/09 08:00 with nothing recorded in between - almost
certainly an unrecorded dilution/passage step, not actual die-off. That
gap is called out in the extract's own `comments` column on the affected
rows, row by row, rather than only in this docstring. It also means a
doubling-time fit spanning that gap is not biologically meaningful; no
special-case code drops it, since `_fit_growth_rate` already only reports
a doubling time when the overall regression slope is positive; a fit
dominated by that gap comes out non-positive and is filtered out by the
dashboard's existing `doubling_time_hr > 0` check the same as any other
bad fit would be, with the gap called out here in case a future point
makes that automatic filter matter less.

Mutant, media, condition
--------------------------
A growth curve here is defined by three things: which mutant/strain it is
(the existing `strain` column), which media it was grown in, and
optionally some other special condition (a perturbation like lights off,
reserved for the future - nothing in this corpus sets it yet). Only
raw_exports/coimbra_growth_curves.csv records its own media (BG-11 or
TAP); every other surviving file defaults to `media = "TAP"` (the lab's
standard media, per Yatharth's "assume TAP wherever not mentioned" rule)
since none of them record it explicitly. `condition` is written as an
empty string until something needs it.

Cell density - unchanged from the original pipeline
----------------------------------------------------
This reproduces legacy/script/analysis.py's normalize_cells_per_ml() exactly:

    avg_count       = mean(count1..4), ignoring blanks
    count_norm      = avg_count * (v_sample_ul + v_etoh_ul) / v_sample_ul
    density         = count_norm / HCM_CONSTANTS["total_vol_ml"]

`inv_dil` (a real column in the source files - the dilution the sample was
prepared at before counting, recorded as its reciprocal: 1000 means diluted
1:1000) is not part of this formula, and never was: it appears exactly once
in legacy/script/analysis.py, as a dataclass field with a comment
documenting what it means, and is never read again anywhere in that file or
in main.py. An earlier version of *this* script assumed it was a forgotten
multiplier and applied it - that assumption was wrong, per Yatharth; the
fix was to stop applying it, and it is now dropped from the output
entirely rather than carried through unused, since it was never part of
any calculation to begin with. The raw `inv_dil` value is still read
internally, purely as a signal for detecting placeholder rows (see
`all_zero_untagged` below) - it just isn't exposed as a column.

Output (repo root, gitignored, rebuilt on every run):
    build/all_legacy_counts.csv
        source_file, strain, media, condition, label, date, time, timestamp,
        exp_time, time_units, avg_count, v_sample_ul, v_etoh_ul, density,
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

DEFAULT_MEDIA = "TAP"

# The curated, git-tracked extract of coimbra.csv's real growth-curve rows
# (see the module docstring's "BG-11 media" section) - parsed by
# _parse_coimbra_growth below instead of the generic _parse_file, since its
# schema (strain, media, date, time, df, avg_count, density_per_mL,
# comments) is already-aggregated and unrelated to template1's.
COIMBRA_GROWTH_FILE = "raw_exports/coimbra_growth_curves.csv"

# Files that pass the density-column check but are not growth curves - a
# protocol test or a counting-method validation run, not a strain/mutant
# comparison over time - and so are excluded outright, per Yatharth. See
# the module docstring for why each one specifically.
EXCLUDED_FILES = {
    "raw_exports/centrifugation_10pow4_RepAB_Controls.csv":
        "centrifugation/recovery protocol test, not a growth curve",
    "ProtocolGrowthCurve_Exp1_F13Xseries.csv":
        "counting-protocol development run, not a strain comparison",
    "raw_exports/YB_E0.csv": "counting-protocol development run",
    "raw_exports/YB_E4.csv": "counting-protocol development run",
    "raw_exports/YB_E4noEtOH.csv": "counting-protocol development run",
    "raw_exports/YB_E5noEtOH.csv": "counting-protocol development run",
    "raw_exports/YB_N0.csv": "counting-protocol development run",
    "raw_exports/YB_test.csv": "counting-protocol development run",
    "raw_exports/coimbra.csv":
        "33MB raw instrument export, not tracked in git; its 30 real "
        "growth-curve rows are already extracted into "
        "raw_exports/coimbra_growth_curves.csv, which is parsed instead",
}


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
    # inv_dil is read above only to help flag placeholder rows - it's not
    # part of the density calculation (see module docstring) and is dropped
    # entirely from the output below, not carried through.

    count_norm = avg_count * (v_sample + v_etoh) / v_sample
    density = count_norm / HCM_CONSTANTS["total_vol_ml"]

    timestamps = [
        _parse_timestamp(d, t)
        for d, t in zip(kept.get("date", pd.Series(dtype=str)), kept.get("time", pd.Series(dtype=str)))
    ]
    timestamps = pd.Series(timestamps, index=kept.index)
    n_bad_dates = int(timestamps.isna().sum())

    # media: use the file's own column if it ever has one; otherwise every
    # row defaults to DEFAULT_MEDIA (see module docstring). condition is
    # reserved for a future perturbation label (e.g. "lights off") - nothing
    # in this corpus sets it yet, so it's blank.
    if "media" in kept.columns:
        media = kept["media"].astype(str).str.strip()
    else:
        media = pd.Series([DEFAULT_MEDIA] * len(kept), index=kept.index)
    condition = kept.get("condition", pd.Series([""] * len(kept), index=kept.index)).astype(str)

    out = pd.DataFrame({
        "source_file": os.path.relpath(path, LEGACY_DATA_DIR),
        "strain": kept.get("strain", pd.Series(dtype=str)).astype(str).str.strip(),
        "media": media,
        "condition": condition,
        "label": kept.get("replicate", pd.Series(dtype=str)).astype(str).str.strip(),
        "date": kept.get("date"),
        "time": kept.get("time"),
        "timestamp": timestamps,
        "exp_time": kept.get("exp_time", pd.Series(dtype=float)).apply(_to_float),
        "time_units": kept.get("time_units", pd.Series([""] * len(kept))).astype(str),
        "avg_count": avg_count,
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


def _parse_coimbra_growth(path):
    """raw_exports/coimbra_growth_curves.csv - see the module docstring's
    "BG-11 media" section. Already one row per reading with strain, media,
    date, time, df, avg_count and a precomputed density_per_mL (the
    original file's own formula - avg_count * df * 10_000 - not this
    script's v_sample/v_etoh one), so this is a straight column mapping,
    not a re-derivation. `label` is set to `media`: this file has no
    recorded replicate id, and media is the only thing that distinguishes
    the two curves per strain, so it doubles as the colony/replicate label
    everywhere downstream that groups by (source_file, strain, label)."""
    df = pd.read_csv(path)
    n = len(df)
    timestamps = pd.Series(
        [_parse_timestamp(d, t) for d, t in zip(df["date"], df["time"])],
        index=df.index,
    )
    media = df["media"].astype(str).str.strip()
    out = pd.DataFrame({
        "source_file": os.path.relpath(path, LEGACY_DATA_DIR),
        "strain": df["strain"].astype(str).str.strip(),
        "media": media,
        "condition": [""] * n,
        "label": media,
        "date": df["date"],
        "time": df["time"],
        "timestamp": timestamps,
        "exp_time": pd.Series([np.nan] * n),
        "time_units": pd.Series([""] * n),
        "avg_count": df["avg_count"].apply(_to_float),
        "v_sample_ul": pd.Series([np.nan] * n),
        "v_etoh_ul": pd.Series([np.nan] * n),
        "density": df["density_per_mL"].apply(_to_float),
        "comments": df.get("comments", pd.Series([""] * n)).astype(str).replace("nan", ""),
    })
    out = out.dropna(subset=["timestamp", "density"])
    note = f"{len(out)} usable row(s) kept (BG-11 vs TAP comparison, extracted from coimbra.csv)"
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
    """One row per (source_file, strain, media, label) with enough points to
    fit - the legacy-side counterpart of build/all_growth_summary.csv.
    `media` is in the group key (not just `label`) so that a file recording
    more than one media for the same strain - only
    raw_exports/coimbra_growth_curves.csv does today - never gets its BG-11
    and TAP readings folded into one fit; harmless for every other file,
    where media is constant per strain anyway.

    Skips any group whose time_units reads "mins" - a "doubling time" fit to
    an hour of data would not be biologically meaningful even though the
    regression happily produces one. Nothing in the corpus currently hits
    this (the one file that did, the centrifugation protocol test, is now
    excluded outright by EXCLUDED_FILES - see the module docstring), but
    it's kept as a defensive check for whatever gets added next."""
    rows = []
    n_skipped_short = 0
    for (source_file, strain, media, label), sub in combined.groupby(
        ["source_file", "strain", "media", "label"]
    ):
        units = sub["time_units"].astype(str).str.strip().str.lower()
        if (units == "mins").any():
            n_skipped_short += 1
            continue
        fit = _fit_growth_rate(sub)
        if fit is None:
            continue
        rows.append({"source_file": source_file, "strain": strain, "media": media,
                      "label": label, **fit})
    if n_skipped_short:
        print(f"  ({n_skipped_short} colony/replicate group(s) skipped for growth-rate fitting - "
              f"minute-scale assay, not a growth curve)")
    if not rows:
        return pd.DataFrame(columns=["source_file", "strain", "media", "label", "n_points",
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
        rel = os.path.relpath(path, LEGACY_DATA_DIR)
        if rel in EXCLUDED_FILES:
            print(f"  {rel}: excluded - {EXCLUDED_FILES[rel]}")
            continue
        try:
            if rel == COIMBRA_GROWTH_FILE:
                out, note = _parse_coimbra_growth(path)
            else:
                out, note = _parse_file(path)
        except Exception as exc:  # a malformed file must never take the rest down
            print(f"  {path}: SKIPPED ({exc})")
            continue
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
