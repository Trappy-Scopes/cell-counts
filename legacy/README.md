# legacy

The pipeline this repository used before it adopted the Trappy-Scopes
experiment framework (`Experiment.Construct`, measurement streams, and
`cellcounting.py` — see the root `README.md`).

Counts were entered by hand into a per-experiment CSV copied from
`templates/template1.csv`, and processed by the scripts in `script/` — a
fixed pipeline of file-hash tracking (`hasher.py`, `filelogs.yml`), Excel
extraction (`excel.py`), averaging and per-mL conversion (`main.py`,
`analysis.py`), and exponential fits (`plot.py`). `new_counting.py` was the
CLI for starting a new count from the template.

Nothing here runs as part of the current site or its CI. It is kept for
provenance — some of the growth-rate and dilution logic in the current
`cellcounting.py` descends from `analysis.py` and `plot.py` — and because
`data/` (below) holds real counts that predate the current framework and
have not been re-entered into it.

## Contents

| | |
|---|---|
| `script/` | the old processing pipeline |
| `templates/` | the CSV template `new_counting.py` copied from |
| `notebooks/` | `dev.ipynb`, `Growth Curves.ipynb` — exploratory analysis |
| `archive/` | `Counting_Cells.xlsx`, an early hand-kept spreadsheet |
| `data/` | old-format counts (`10pow4exp1.csv`, `TheEight.csv`, and others) |
| `data/raw_exports/` | counter/instrument dumps kept locally only — see below |
| `action.yaml` | the original GitHub Actions workflow (`run main.py` on push, committing results back to `main`) |
| `requirements.txt` | what `script/` needs: `numpy==1.21.5` |
| `filelogs.yml` | file-hash cache `hasher.py` used to skip already-processed files |

## `data/raw_exports/`

Three files here — `coimbra.csv`, `october24.csv`, `september24.csv` — are
~33 MB instrument exports and are **not tracked in git** (see
`.gitignore`); they exist only in this local working copy. If they need to
be versioned, use Git LFS or attach them as a release asset rather than
committing them directly — GitHub's per-file limit is 100 MB and a repo
this size would make every clone slow. Everything else in `data/` is small
and tracked normally.

## The original branch

The full pre-restructure repository — before this `legacy/` folder existed
and before `data/` held the current framework's experiment folders — is
preserved as the `legacy` branch, untouched.
