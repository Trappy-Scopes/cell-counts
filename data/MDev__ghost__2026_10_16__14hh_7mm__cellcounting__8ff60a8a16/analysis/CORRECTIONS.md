# Corrections to this run's exported data (2026-10-30)

`experiment.yaml` (the raw log) is **unchanged**. The CSVs and plots in this
folder were regenerated from the log's values with two timestamp corrections
to the `media_additions` stream (all 9 rows):

1. **Year typo.** Two media additions (C1-22Sept26, D1-22Sept26) were logged as
   `0026-10-06 16:15`. Corrected to 2026. (This had stretched the combined
   growth-curve x-axis to about -1.75e7 hours and crashed `tools/parse_data.py`.)
2. **Dilution time.** Every dilution (6, 7, 8 Oct) was logged at 16:15 / 15:10 /
   16:00, earlier than the 17:30 counts. The counts were taken *before* each
   day's dilution, so every dilution time was set to 18:00. Without this the
   Oct 6 counts were wrongly multiplied by the dilution fold (x20 / x5).

Counts, df, density, labels and conditions are exactly as logged. The
`note` column in `media_additions.csv` records the original timestamp of each row.
Pre-correction analysis outputs are kept in `../analysis_uncorrected/`.
Condition: DCMU is 10 uM (note #1 in the log says "10mM"; the `condition` field says 10uM).
