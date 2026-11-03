"""
axisbreaks.py - automatic x-axis breaks for Bokeh datetime plots.

Growth data here comes in bursts: a few days of counts, then weeks or months of
nothing, then another burst. On a real-time axis the bursts are squeezed into thin
slivers and most of the plot is empty. Bokeh has no native axis break, so this module
fakes one: x is replaced by a *compressed* coordinate in which every long empty stretch
is collapsed to a short, fixed-width gap (and a very short burst of data is stretched to a minimum width so it stays legible), and the tick labels are rebuilt from the real
dates (so a tick always reads as the true date, never as the compressed number).

    ctrl = axisbreaks.add_axis_breaks(fig)      # call after every renderer is on `fig`
    layout = column(..., ctrl, fig) if ctrl is not None else column(..., fig)

What it does to `fig`:
  * finds the breaks automatically: taking the longest gaps between consecutive data points
    (or event markers) first, a gap is a break while it is at least min_gap_days long and at
    least min_gap_frac of the axis that would remain once it is cut out (at most max_breaks).
    No break found -> returns None and leaves `fig` exactly as it was.
  * starts compacted, and returns a "Compact gaps | Real time" switch; picking
    "Real time" restores the ordinary datetime axis (data, ticks, range, event markers),
    picking "Compact gaps" collapses the breaks again. The toolbar's reset tool returns
    to the full view of whichever mode is active.
  * marks each break with a dotted vertical line labelled with the length of the gap.

It only touches x. Hover tooltips that print a timestamp keep printing the real one as
long as they use a string column (all of this repo's plots do).
"""

import numpy as np
import pandas as pd

HOUR, DAY = 3_600_000, 86_400_000
_STEPS = [1 * HOUR, 2 * HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR, 1 * DAY, 2 * DAY, 3 * DAY,
          7 * DAY, 14 * DAY]
_EPOCH = pd.Timestamp("1970-01-01")


def _to_ms(values):
    """datetime-like or numeric (ms since epoch) -> float64 ms array (NaN kept)."""
    arr = pd.Series(values)
    if pd.api.types.is_datetime64_any_dtype(arr):
        idx = pd.DatetimeIndex(arr)
        out = np.asarray((idx - _EPOCH) / pd.Timedelta(milliseconds=1), dtype="float64")
        out[idx.isna()] = np.nan
        return out
    return np.asarray(arr, dtype="float64")


def _field_of(spec):
    if isinstance(spec, str):
        return spec
    return getattr(spec, "field", None)


def _fmt_gap(ms):
    days = ms / DAY
    if days < 2:
        return f"{ms / HOUR:.0f} h gap"
    if days < 60:
        return f"{days:.0f} d gap"
    return f"{days / 30.4:.0f} mo gap"


class _Compressor:
    """Piecewise-linear map real ms -> compressed ms. Every segment keeps its own linear
    time scale; a segment shorter than `min_seg` (e.g. one single day in a plot that spans
    years) is stretched up to `min_seg` so it stays readable, and a zero-length segment
    (all its points at one instant) is centred in a `min_seg`-wide slot. Breaks are `pad`
    wide."""

    def __init__(self, starts, ends, pad, min_seg):
        self.starts, self.ends, self.pad = np.array(starts), np.array(ends), pad
        lens = self.ends - self.starts
        eff = np.maximum(lens, min_seg)
        self.scale = np.where(lens > 0, eff / np.where(lens > 0, lens, 1.0), 1.0)
        self.centre = (eff - lens * self.scale) / 2          # only non-zero for zero-length segments
        self.eff = eff
        self.offset = [starts[0]]
        for k in range(len(starts) - 1):
            self.offset.append(self.offset[-1] + eff[k] + pad)
        self.offset = np.array(self.offset)

    def __call__(self, t):
        t = np.asarray(t, dtype="float64")
        k = np.clip(np.searchsorted(self.starts, t, side="right") - 1, 0, len(self.starts) - 1)
        inside = np.minimum(t - self.starts[k], self.ends[k] - self.starts[k])
        return self.offset[k] + inside * self.scale[k] + self.centre[k]

    def break_centres(self):
        return [self.offset[k] + self.eff[k] + self.pad / 2 for k in range(len(self.starts) - 1)]


def _ticks_for_segment(s, e, long_span):
    """[(real_ms, label)] for one segment: the smallest nice step with <= 4 ticks."""
    lo, hi = pd.Timestamp(s, unit="ms"), pd.Timestamp(e, unit="ms")
    ticks = None
    for step in _STEPS:
        if step < DAY and (e - s) >= 2 * DAY:        # a multi-day segment is labelled by day, not by hour
            continue
        first = np.ceil(s / step) * step
        cand = np.arange(first, e + 1, step)
        if 1 <= len(cand) <= 4:
            ticks = [(float(c), step) for c in cand]
            break
    if ticks is None:                              # longer than any fixed step: month/quarter/year starts
        for freq in ("MS", "QS", "YS"):
            cand = pd.date_range(lo.ceil("D"), hi, freq=freq)
            if 1 <= len(cand) <= 4:
                ticks = [(float((c - _EPOCH) / pd.Timedelta(milliseconds=1)), 30 * DAY) for c in cand]
                break
    if not ticks:                                  # segment shorter than its step: label its start
        ticks = [(float(s), HOUR if (e - s) > 0 and (e - s) < 2 * DAY else DAY)]
    out = []
    for t, step in ticks:
        ts = pd.Timestamp(t, unit="ms")
        if step < DAY:
            label = ts.strftime("%d %b %H:%M")
        elif step >= 30 * DAY:
            label = ts.strftime("%b %Y")
        else:
            label = ts.strftime("%d %b %y" if long_span else "%d %b")
        out.append((t, label))
    return out


def add_axis_breaks(fig, min_gap_days=2.0, min_gap_frac=0.10, max_breaks=8, compact_by_default=True):
    """Add automatic x-axis breaks to a datetime Bokeh figure. Returns a layout item
    (the Compact/Real switch) or None when the data has no break worth making."""
    from bokeh.models import (CustomJS, Div, FixedTicker, GlyphRenderer, Label, Range1d,
                              RadioButtonGroup, Span)
    from bokeh.layouts import row

    # --- 1. every x the figure draws: (source, field) pairs, plus event markers ----------
    pairs, seen = [], set()
    for r in fig.renderers:
        if not isinstance(r, GlyphRenderer):
            continue
        field = _field_of(getattr(r.glyph, "x", None))
        if field is None or field not in r.data_source.data or (id(r.data_source), field) in seen:
            continue
        seen.add((id(r.data_source), field))
        pairs.append((r.data_source, field))
    markers = [m for m in fig.center
               if (isinstance(m, Span) and m.dimension == "height") or isinstance(m, Label)]
    marker_x = [(m, "location" if isinstance(m, Span) else "x") for m in markers]
    if not pairs:
        return None

    real = {(id(s), f): _to_ms(s.data[f]) for s, f in pairs}
    anchors = np.concatenate([v[~np.isnan(v)] for v in real.values()] +
                             [np.array([float(getattr(m, p))]) for m, p in marker_x])
    t = np.unique(anchors)
    if len(t) < 2:
        return None

    # --- 2. breaks -----------------------------------------------------------------------
    # Largest gaps first; a gap becomes a break while it is at least `min_gap_frac` of the
    # axis that would be left after cutting it out (i.e. it wastes a real share of the plot)
    # and at least `min_gap_days` long. Capped at `max_breaks` so a scattered series doesn't
    # turn into a comb.
    span = t[-1] - t[0]
    gaps = np.diff(t)
    chosen, remaining = [], span
    for i in np.argsort(gaps)[::-1][:max_breaks]:
        left = remaining - gaps[i]
        if gaps[i] < min_gap_days * DAY or gaps[i] < min_gap_frac * max(left, 1.0):
            break
        chosen.append(i)
        remaining = left
    cut = np.array(sorted(chosen), dtype=int)
    if len(cut) == 0:
        return None
    starts = [t[0]] + [t[i + 1] for i in cut]
    ends = [t[i] for i in cut] + [t[-1]]
    kept = float(sum(e - s for s, e in zip(starts, ends)))
    comp = _Compressor(starts, ends, pad=max(0.04 * kept, 6 * HOUR), min_seg=max(0.03 * kept, 3 * HOUR))
    long_span = span > 300 * DAY

    # --- 3. compressed columns; the glyphs read "<field>__cur" ---------------------------
    sources, fields = [], []
    for s, f in pairs:
        r_ms = real[(id(s), f)]
        s.data = {**dict(s.data), f"{f}__real": r_ms, f"{f}__comp": comp(r_ms),
                  f"{f}__cur": comp(r_ms) if compact_by_default else r_ms}
        sources.append(s)
        fields.append(f)
    for r in fig.renderers:
        if isinstance(r, GlyphRenderer):
            f = _field_of(getattr(r.glyph, "x", None))
            if f is not None and (id(r.data_source), f) in seen:
                r.glyph.x = f + "__cur"

    # --- 4. ticks, labels and break marks for the compact view --------------------------------
    # compact range first (needed to thin ticks that would otherwise print on top of each other)
    cs, ce = float(comp(t[0])), float(comp(t[-1]))
    min_spacing = 0.075 * (ce - cs)
    cand = []
    for k in range(len(starts)):
        for real_t, label in _ticks_for_segment(starts[k], ends[k], long_span):
            cand.append((int(round(float(comp(real_t)))), label))
    tick_pos, overrides, last = [], {}, None
    for pos, label in sorted(cand):
        if last is None or pos - last >= min_spacing:
            tick_pos.append(pos)
            overrides[pos] = label
            last = pos
    fixed_ticker = FixedTicker(ticks=tick_pos)

    break_models, last_label = [], None
    for k, centre in enumerate(comp.break_centres()):
        gap_ms = starts[k + 1] - ends[k]
        line = Span(location=centre, dimension="height", line_color="#888888",
                    line_dash="dotted", line_width=1.2, visible=compact_by_default)
        fig.add_layout(line)
        break_models.append(line)
        if last_label is None or centre - last_label >= 0.04 * (ce - cs):   # label breaks that aren't crowded
            text = Label(x=centre, y=(fig.height or 400) / 2, y_units="screen", angle=1.5708,
                         text=f" {_fmt_gap(gap_ms)} ", text_font_size="8pt", text_color="#666666",
                         text_align="center", background_fill_color="white",
                         background_fill_alpha=0.7, visible=compact_by_default)
            fig.add_layout(text)
            break_models.append(text)
            last_label = centre

    # event markers (vertical lines / labels at fixed dates) move with the axis
    ev_models = [m for m, _ in marker_x]
    ev_props = [p for _, p in marker_x]
    ev_real = [float(getattr(m, p)) for m, p in marker_x]
    ev_comp = [float(comp(v)) for v in ev_real]
    if compact_by_default:
        for m, p, c in zip(ev_models, ev_props, ev_comp):
            setattr(m, p, c)

    # --- 5. ranges ---------------------------------------------------------------------------------
    def padded(a, b):
        m = 0.03 * (b - a)
        return a - m, b + m
    rs, re_ = padded(t[0], t[-1])
    cs, ce = padded(cs, ce)
    start, end = (cs, ce) if compact_by_default else (rs, re_)
    fig.x_range = Range1d(start=start, end=end, reset_start=start, reset_end=end)

    axis = fig.xaxis[0]
    orig_ticker = axis.ticker
    if compact_by_default:
        axis.ticker = fixed_ticker
        axis.major_label_overrides = overrides

    # --- 6. the switch --------------------------------------------------------------------------------
    switch = RadioButtonGroup(labels=["Compact gaps", "Real time"],
                              active=0 if compact_by_default else 1, width=240)
    switch.js_on_change("active", CustomJS(args=dict(
        sources=sources, fields=fields, axis=axis, xr=fig.x_range,
        fixed_ticker=fixed_ticker, orig_ticker=orig_ticker, overrides=overrides,
        break_models=break_models, ev_models=ev_models, ev_props=ev_props,
        ev_real=ev_real, ev_comp=ev_comp,
        r_range=[rs, re_], c_range=[cs, ce]), code="""
        const compact = (cb_obj.active === 0);
        for (let i = 0; i < sources.length; i++) {
            const s = sources[i], f = fields[i];
            s.data = Object.assign({}, s.data, {[f + "__cur"]: compact ? s.data[f + "__comp"] : s.data[f + "__real"]});
        }
        axis.ticker = compact ? fixed_ticker : orig_ticker;
        axis.major_label_overrides = compact ? overrides : new Map();
        for (const m of break_models) { m.visible = compact; }
        for (let i = 0; i < ev_models.length; i++) {
            ev_models[i][ev_props[i]] = compact ? ev_comp[i] : ev_real[i];
        }
        const rg = compact ? c_range : r_range;
        xr.reset_start = rg[0]; xr.reset_end = rg[1];
        xr.start = rg[0]; xr.end = rg[1];
    """))
    return row(Div(text="<small>Time axis</small>", styles={"padding-top": "6px"}), switch)
