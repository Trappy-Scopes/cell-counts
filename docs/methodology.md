# Methodology

## Dilution compensation

Cells are counted from a fixed-volume sample, so the raw `density` column
is only meaningful until media gets added — after that, the same number of
cells is spread through more liquid and density drops for a reason that has
nothing to do with growth.

Each media addition is logged separately (`log_media_addition`) as a
volume-before and a volume-added, not a growth measurement. From those two
numbers:

```
dilution_fraction = media_added_ml / (volume_before_ml + media_added_ml)
fold_factor        = 1 / (1 - dilution_fraction)
```

`fold_factor` is how much the density of an unchanged population would
appear to drop from this one addition. To compensate a given count, every
`fold_factor` for media added *before* that count's timestamp is multiplied
onto the raw density:

```
compensated_density = raw_density × Π(fold_factor for every prior addition)
```

The result is what the density *would have read* if no media had ever been
added — a single continuous trace suitable for one exponential fit, which
is the `compensated_density` column in `cell_counts.csv` and what every
plot on this site actually shows.

## Fitting the growth rate

Exponential growth means `dN/dt = μN`, which integrates to
`N(t) = N₀·e^(μt)` — so `ln(N(t))` is linear in `t` with slope `μ`. Fitting
is therefore an ordinary least-squares line through
`ln(compensated_density)` vs. elapsed hours (`np.polyfit`); the slope is
`growth_rate_per_hr`, and `r_squared` says how well the data actually held
to that constant-rate assumption.

Two figures follow directly from `μ`:

- **doubling time** `= ln(2) / μ` — hours for the population to double.
- **growth rate per 24 h** `= μ × 24` — the same rate constant on a
  different clock, valid because it is a rescaling of the exponent, not a
  linear conversion of a fold-change (`N(t+24)/N(t) = e^(24μ)` either way).

## Continuously diluted cultures

Some colonies get media added repeatedly rather than once — Gptx above,
diluted on all three retrieval days. Fitting *one* slope across the whole
compensated trace still works, but it hides whether the rate held steady
from one dilution to the next or drifted.

The direct fix does not need new bookkeeping: because
`compensated_density` is already reconstructed as one continuous trace,
the ratio between two *consecutive* readings —
`compensated[i+1] / compensated[i]` — is already the locally
dilution-corrected growth ratio for exactly that interval (every earlier
cumulative fold-factor cancels out of the ratio). So the segment-wise rate
between reading `i` and `i+1` is just:

```
segment_rate = ln(compensated[i+1] / compensated[i]) / Δt_hours
```

computed once per consecutive pair, with no re-derivation of fold factors
needed. `growth_rate_segments()` and `plot_growth_rate_segments()` do
exactly this, and run automatically for any colony with two or more media
additions — see `Gptx_segment_growth_rate.png` on the
[growth curves page](growth-curves.md#per-experiment-detail).
