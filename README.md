# Portfolio - econometrics workflow

This repository supports the VN100 asset-pricing and portfolio project described in the project brief. The econometrics team's Steps 1-6 use Kenneth French data to validate the CAPM, FF3, FF5, GRS, HAC, and VIF workflow. Factor Team outputs for Vietnam are now present in `outputs/vn_period_factors/`; the econometrics runner produces a clearly labelled provisional Step 7 result while the final 30-asset universe and method choices are reviewed.

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
outputs/               Tables and audit reports for Steps 1-6 and VN factor/model runs
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

The separate Factor Team demonstration snapshot lives in `data/test/factor_demo/` and is read by `scripts/run_us_factor_demo.py`.

## Run the Vietnam econometrics workflow

The paired Factor Team inputs are `outputs/vn_period_factors/vn100_returns_clean.csv` and `outputs/vn_period_factors/vn100_factors_monthly.csv`. Returns, RF, and factors are stored as decimals. The current factor file has 96 months of CAPM/FF3 inputs and 60 months complete for FF5 (2021-07 through 2026-06). The baseline comparison uses those same 60 months for all three models.

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py
```

This command selects 30 tickers with complete common-period returns, ranked by source-month coverage. It writes a **provisional technical result** to `outputs/vn_econometrics_provisional/`: 90 asset regressions, HAC lag 12/6, VIF, three GRS tests, an HML spanning regression, Table 5/7-style CSVs, selected tickers, sample months, a run manifest, and a report. The output folder records the Factor Team commit and input SHA-256 values.

For a group-approved set of 30 tickers, create `config/vn_econometrics_universe.csv` with one `ticker` column and exactly 30 distinct values, then run:

```powershell
.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py --universe config\vn_econometrics_universe.csv --output-dir outputs\vn_econometrics_review
```

The runner rejects missing ticker-month returns. It still marks an explicit universe as requiring review until the project lead approves the factor definitions and sample. Current Factor Team defaults use VNINDEX for MKT, a 1Y government yield converted to monthly RF, June formation, July-to-June holding, and lagged market-cap weights; see `docs/vn_period_factor_pipeline.md` and the run report. These choices need to be reported as used, especially where they differ from the project brief.

## Results and known boundary

The final consolidated review is [`outputs/full_audit_steps1_6.md`](outputs/full_audit_steps1_6.md). Step-specific results are in `outputs/step3_*` through `outputs/step6_*`; the earlier Steps 1-5 review is retained under [`outputs/history/`](outputs/history/).

Comparisons with Fama-French (2015) are approximate because the current 25-portfolio LHS file has no vintage metadata and has not been verified as the exact 2015 file. The US test data is not Vietnam research data. Vietnam results are in `outputs/vn_econometrics_provisional/`; its 30-stock selection is a technical sample until the group supplies the official LHS universe.
