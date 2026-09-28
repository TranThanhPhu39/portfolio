# Portfolio - econometrics workflow

This repository supports the VN100 asset-pricing and portfolio project described in the project brief. The econometrics team's completed Steps 1-6 use Kenneth French data to validate the CAPM, FF3, FF5, GRS, HAC, and VIF workflow. Step 7 is pending delivery of Vietnam returns and Vietnam factors.

## Audit entry point

Start with [`docs/econometrics_audit_guide.md`](docs/econometrics_audit_guide.md). It maps each checklist step to its inputs, implementation, saved output, and completion evidence. [`data/README.md`](data/README.md) explains which files are test inputs and which are historical references.

For a cell-by-cell review of the econometrics workflow, open [`notebooks/03_asset_pricing_tests.ipynb`](notebooks/03_asset_pricing_tests.ipynb).

## Repository layout

```text
data/                  Test inputs and historical references
docs/                  Method and audit documentation
config/                Project configuration and universe
src/                   Reusable data, factor, model, portfolio, and backtest code
scripts/               Reproducible workflow entry points
notebooks/             Econometrics Step 3 audit notebook
outputs/               Tables and audit reports for Steps 1-6
tests/                 Existing project tests
requirements.txt       Pinned runtime dependencies
requirements.lock.txt  Resolved Python 3.12.14 environment
```

The Step 3 notebook is an audit view over the same reusable functions and saved tables. Scripts under `scripts/` remain the repeatable workflow entry points.

## Set up on Windows

Use Python 3.12.14 as recorded in `.python-version`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

## Reproduce Steps 3-6

The committed snapshot under `data/test/` lets reviewers run the analyses immediately. From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\compare_factor_models.py
.\.venv\Scripts\python.exe scripts\compare_to_fama_french_2015.py
.\.venv\Scripts\python.exe scripts\run_grs_test.py
.\.venv\Scripts\python.exe scripts\run_step6_diagnostics.py
```

To fetch a fresh Kenneth French sample and the separate US factor-sorting logic sample, run:

```powershell
.\.venv\Scripts\python.exe scripts\get_test_data.py
```

The fetcher writes to `data/test/kenneth_french/` and `data/test/us_factor_logic/`. It does not replace the historical reference archives under `data/reference/`.

## Results and known boundary

The final consolidated review is [`outputs/full_audit_steps1_6.md`](outputs/full_audit_steps1_6.md). Step-specific results are in `outputs/step3_*` through `outputs/step6_*`; the earlier Steps 1-5 review is retained under [`outputs/history/`](outputs/history/).

Comparisons with Fama-French (2015) are approximate because the current 25-portfolio LHS file has no vintage metadata and has not been verified as the exact 2015 file. Step 7 must wait for the Vietnam dataset; the test data in this repository is not Vietnam research data.
