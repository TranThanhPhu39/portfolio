# Econometrics team audit guide

This guide maps the team's checklist to the repository files. Read it with [`../data/README.md`](../data/README.md) and the final consolidated report [`../outputs/full_audit_steps1_6.md`](../outputs/full_audit_steps1_6.md).

The cell-by-cell review is [`../notebooks/03_asset_pricing_tests.ipynb`](../notebooks/03_asset_pricing_tests.ipynb).

## Checklist map

| Step | Input | Implementation | Saved evidence | Status |
|---|---|---|---|---|
| 1. Identify the 25 LHS portfolios | [25-portfolio CSV](../data/test/kenneth_french/25_portfolios_size_bm.csv) | Column layout and labels documented in the full audit | [Full audit](../outputs/full_audit_steps1_6.md) | Pass on the test file |
| 2. General factor regression | 25-portfolio CSV and [FF3](../data/test/kenneth_french/ff3_factors_monthly.csv) / [FF5](../data/test/kenneth_french/ff5_factors_monthly.csv) factor CSVs | [Regression module](../src/models/regressions.py) | `model.summary()` and regression details in the [full audit](../outputs/full_audit_steps1_6.md) | Pass on the test sample |
| 3. CAPM, FF3, FF5 comparison | One LHS column and matching monthly factors | [Comparison runner](../scripts/compare_factor_models.py) | [Comparison table](../outputs/step3_model_comparison.csv) | Pass; observed R-squared increases CAPM < FF3 < FF5 |
| 4. Compare with Fama-French (2015) | Current LHS, FF3/FF5 factors, and the [historical factor archives](../data/reference/kenneth_french/) | [Comparison runner](../scripts/compare_to_fama_french_2015.py) | [Audit](../outputs/step4_audit.md), [Table 5 comparison](../outputs/step4_table5_panel_a_comparison.csv), [Table 7 comparison](../outputs/step4_table7_comparison.csv) | Pass as an approximate comparison; LHS vintage limitation is recorded |
| 5. Joint GRS test for 25 portfolios | 25 LHS columns, FF3/FF5 factors, and historical factor archives | [GRS module](../src/models/grs_test.py), [runner](../scripts/run_grs_test.py) | [Audit](../outputs/step5_grs_audit.md), [results](../outputs/step5_grs_results.csv) | Pass; current-data and historical-factor sensitivity results are reported |
| 6. HAC and VIF diagnostics | `SMALL LoBM` plus the matching factor files | [Diagnostics module](../src/models/diagnostics.py), [runner](../scripts/run_step6_diagnostics.py) | [Audit](../outputs/step6_audit.md), [HAC results](../outputs/step6_hac_results.csv), [VIF results](../outputs/step6_vif.csv) | Pass on the test sample |
| 7. Run on Vietnam data | [Clean returns](../outputs/vn_period_factors/vn100_returns_clean.csv) and [monthly factors](../outputs/vn_period_factors/vn100_factors_monthly.csv) from Factor Team | [VN runner](../scripts/run_vn_econometrics.py) calls the shared regression, HAC/VIF, and GRS modules | [Provisional run report](../outputs/vn_econometrics_provisional/run_report.md), [asset models](../outputs/vn_econometrics_provisional/asset_model_summary.csv), [GRS](../outputs/vn_econometrics_provisional/grs_summary.csv) | Technical run passes on 30 coverage-selected tickers and 60 common months; final universe and factor-method sign-off remain open |

## Reproduction order

Install the pinned environment using the commands in the root README, then run these from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\compare_factor_models.py
.\.venv\Scripts\python.exe scripts\compare_to_fama_french_2015.py
.\.venv\Scripts\python.exe scripts\run_grs_test.py
.\.venv\Scripts\python.exe scripts\run_step6_diagnostics.py
.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py
```

Each runner reads the committed inputs under `data/` and writes its tables and report to `outputs/`. Run `scripts/get_test_data.py` only when refreshing the current test sample; the historical archives are versioned separately under `data/reference/`.

## Audit limitation

The current 25-portfolio LHS CSV does not identify its vintage. Historical 2014/2015 factor archives permit factor-vintage sensitivity checks, but they do not turn the LHS into a verified 2015 snapshot. The numerical comparisons with the 2015 paper therefore remain approximate. Vietnam inputs now exist, but the 30-stock selection and the VNINDEX/1Y RF/accounting choices in the Factor Team outputs need group approval before the Step 7 tables can be called final research results.
