# Growth curves

## Interactive

Pan, zoom, hover for exact values, and click a legend entry to hide or show
that colony. One tab per experiment — right now there is one.

<iframe src="../plots/interactive.html" width="100%" height="560" style="border:none;"
        title="Interactive growth curve explorer"></iframe>

[Open full screen →](plots/interactive.html){ .md-button }

**GitHub cannot display this.** README HTML is sanitised, and files viewed
in the repo are shown as source. It is published here, and also uploaded
as a workflow artifact on every run (Actions tab → latest run →
`parsed-data`... the HTML itself is under the job's own artifacts if you
need a copy to open offline).

## Overview

![Growth curves overview](plots/growth_curves_overview.png)

All colonies to date, log-scale density against elapsed time (hours since
each colony's own first reading — experiments start on different dates, so
a shared calendar axis would misalign them). Solid lines had media added at
some point during the run; dashed lines did not. Colour is by mutant.

## Doubling time

![Doubling time summary](plots/doubling_time_summary.png)

Same colonies, one number each: the doubling time implied by the fitted
growth rate (`ln(2) / growth_rate_per_hr`), with the fit's R² alongside it
as a reliability check. See [Methodology](methodology.md) for how the fit
and the dilution compensation behind it actually work.

## Per-experiment detail

`cellcounting.py` also writes a full breakdown for each experiment as it
runs — a per-colony growth curve, a combined plot, a growth-rate-by-mutant
comparison, and, for any colony that had media added more than once, a
segment-wise growth rate across each dilution. These live alongside the
aggregates above and are not duplicated in the two overview figures.

### Cellcounting_2026_09_11_16hh_24mm_f910a2156c

2026-08-18 to 2026-08-21, colonies Eptx, Fptx, Gptx, Hptx, Iptx (all
mutant CC2894). Gptx had media added on all three days and is the one
worth looking at for [segment-wise rates](methodology.md#continuously-diluted-cultures).

<div class="grid" markdown>

![Combined growth curves](plots/Cellcounting_2026_09_11_16hh_24mm_f910a2156c/growth_curves.png)
![Growth rate by mutant](plots/Cellcounting_2026_09_11_16hh_24mm_f910a2156c/growth_rate_by_mutant.png)
![Gptx segment growth rate](plots/Cellcounting_2026_09_11_16hh_24mm_f910a2156c/Gptx_segment_growth_rate.png)

</div>

When a new experiment is added under `data/`, add a matching subsection
here linking to `plots/<experiment-name>/` — the CI step that stages
figures into the site (`.github/workflows/pages.yml`) copies every
experiment's `analysis/*.png` there automatically; only this page's text
needs a human to add it.
