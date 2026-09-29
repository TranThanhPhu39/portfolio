# VN100 econometrics implementation audit

## Source and integration

- Econometrics base: `main` commit `08b7096e4f6971dd58c4c9ca63b2b65a0cf476bf`.
- Factor Team source: `feature/factor-team-tasks-1-7` commit `926f53deaaf0c9cc2e75a540fb789eb1f811d82a`.
- Integration merge: `7695fde` on `vn-econometrics-integration`. The merge retained the econometrics modules and Factor pipeline. The three conflicts were `.gitignore`, `requirements.txt`, and `scripts/get_test_data.py`; the resolved test-data downloader remains the `data/test/` version from the econometrics base.
- Factor Team's demo snapshot was moved from root `test_data/` into `data/test/factor_demo/` to match the repository structure; `scripts/run_us_factor_demo.py` was updated and executed successfully.
- The user-supplied combined ZIP at `E:\Downloads\drive-download-20260929T092926Z-1-001.zip` has SHA-256 `2e0627c061811f96eadbf57a13df6629473b715dd6eb71e9b09e636d6d56180c`. A raw rebuild from this archive reproduced the versioned Factor Team outputs. The econometrics run reads the Factor Team's matched `vn100_returns_clean.csv` and `vn100_factors_monthly.csv` from the same source commit; its manifest checks their Git blobs after line-ending normalization and records SHA-256 values.

## Executed reproducibility checks

| Stage | Executed entry point | Result |
|---|---|---|
| Kenneth French model comparison | `scripts/compare_factor_models.py` | CAPM/FF3/FF5 each fit 606 months; saved comparison CSV matches the pre-merge tracked output. |
| Paper comparison | `scripts/compare_to_fama_french_2015.py` | Table 5/7 comparison CSVs match the pre-merge tracked outputs; vintage limitation remains documented. |
| GRS | `scripts/run_grs_test.py` | 25-portfolio CAPM/FF3/FF5 GRS results reproduced. |
| HAC/VIF | `scripts/run_step6_diagnostics.py` | Lag 12/6 HAC and VIF results reproduced; no factor VIF above 10 in the US test. |
| Factor demo | `scripts/run_us_factor_demo.py` | Code executes after moving the demo inputs under `data/test/factor_demo/`. Small float-string/PNG rendering differences from the Factor Team's committed demo were not retained. |
| VN models, VN100 market baseline | `scripts/run_vn_econometrics.py --market-proxy VN100` | 90 OLS fits (30 assets × 3 models), 360 coefficient rows with HAC lag 12/6, 9 VIF rows, 3 GRS tests, one HML spanning regression, Table 5/7-style outputs, and a VNINDEX sensitivity. All use the same 60 month ends from 2021-07 to 2026-06. |
| Econometrics Team LHS rule | `config/vn_econometrics_universe.csv` | Fixed ex ante: top 30 VN100 members by market cap at June 2021 formation; all 30 have complete return coverage for all 60 following months. |
| Market proxy sensitivity | `outputs/vn_econometrics_baseline/market_proxy_sensitivity.csv` | VN100 and VNINDEX were run on the same assets, RF, factors other than MKT, and months; summary alphas, R², GRS and VIF are preserved. |
| Raw factor rebuild | `scripts/build_vn_period_factors.py` with the user-supplied combined ZIP passed as both inputs | Rebuilt 96 factor months, 800 formation rows, and all 11 output CSVs without altering the archive. Eight CSVs matched the Factor Team commit byte-for-byte after newline normalization; the other three matched in shape/missingness with a maximum numeric gap of `4.44e-16`. |

The VM's pinned runtime used here is Python 3.12.14, pandas 2.2.0, numpy 1.26.0, scipy 1.13.0, statsmodels 0.14.0, openpyxl 3.1.5, and vnstock 3.5.0. `pytest` is absent from this runtime, so no pytest suite was run; the entry-point and result reconciliations above are the executed checks.

## Final independent audit (2026-09-30)

- Re-read the original Econometrics Team checklist in `[gói 1] check tiến độ.xlsx` (sheet `nhóm 2 - KTL`, rows 5–11), the project brief's econometrics outputs and VN100/RF definitions, and the relevant Table 5/7 entries in Fama–French (2015). The reference figures recorded for Steps 4–5 match those tables.
- Recomputed the Kenneth French CAPM/FF3/FF5 regressions, 25-portfolio GRS, lag-12 HAC alpha inference, and RHS VIF directly from the three 606-month test CSVs. The saved Step 3/5/6 figures agree within CSV rounding; the Step 3 R² order and the VIF < 10 criterion hold.
- Independently reconstructed the VN sample from the June 2021 formation audit. The configured tickers are exactly the top 30 by formation market cap, with no later accounting information in that cohort; all 30 have 60 returns, for 1,800 selected stock-month rows. Every selected return uses `close_eom`; seven reported-versus-price gaps exceed one percentage point.
- Independently fitted all 90 VN regressions by matrix least squares and recomputed each model's GRS F/p from the residual and factor covariance matrices. The maximum differences from saved alpha and t-statistic values are 4.63e-10 percentage points and 4.57e-10, respectively, due to CSV rounding. Table 5 aggregates, Table 7 cells, factor betas, HAC z statistics, and VIF rows reconcile to their detailed outputs.
- Re-ran the VN100 entry point into a temporary directory. Twelve of its 13 files are byte-identical to the committed baseline. `model_summaries.txt` differs only in the wall-clock `Time:` fields inserted by statsmodels; its model statistics are unchanged.
- Rechecked the supplied ZIP SHA-256 and the three tracked input hashes in `run_manifest.json`; they match the files currently available. The raw ZIP is not in the PR, while the cleaned return and factor CSVs needed to reproduce the Econometrics Team run are tracked.
- The Factor Team data-quality table flags one return above 100%: VIX.HM in July 2025 is +114.1176%. Its reported and price-derived returns agree to numerical precision. VIX.HM is outside the selected 30-stock LHS, but this source observation can enter factor construction; it remains a flagged source-data observation, not a correction made by the Econometrics Team.

The checklist outputs and checkable completion criteria pass on the supplied data. Exact replication of the 2015 paper remains limited by the unverified vintage of the US LHS file. The VN run uses the documented 1Y-yield monthly RF proxy and the Factor Team's stated formation and weighting rules; these choices must remain explicit when the group reports the empirical findings.

## Checklist status, Steps 1–7

| Step | Status | Evidence against the checklist output / DoD | Remaining action |
|---|---|---|---|
| 1. Understand the 25 LHS portfolios | PASS | `outputs/full_audit_steps1_6.md` maps the 25 Size×B/M columns to rows and columns; it identifies `SMALL LoBM` as the selected test LHS. | None for the test-data DoD. |
| 2. Generic CAPM/FF3/FF5 regression | PASS | `src/models/regressions.py` returns statsmodels results; CAPM/FF3/FF5 each print summaries on the 606-month sample. | None for the test-data DoD. |
| 3. Compare three models on one LHS | PASS | `outputs/step3_model_comparison.csv` reports alpha, t-stat, R² and N; R² is 0.6449 < 0.9171 < 0.9319 on the required US sample. | This ordering is not imposed on VN because FF3 and FF5 use different SMB series. |
| 4. Compare with Fama–French (2015) | PASS WITH LIMITATION | `outputs/step4_audit.md` and the Table 5/7 comparison CSVs report close test-sample results and disclose that the current LHS vintage is not proven to be the exact 2015 file. | Do not describe the comparison as an exact historical replication. |
| 5. GRS on all 25 LHS portfolios | PASS | `outputs/step5_grs_results.csv` contains GRS F and p-values for CAPM/FF3/FF5, with vintage sensitivity; the independent implementation agrees numerically. | None for the test-data DoD. |
| 6. Newey–West and VIF | PASS | `outputs/step6_hac_results.csv` contains lag 12 and lag 6; `outputs/step6_vif.csv` reports all factors below 10. | None for the test-data DoD. |
| 7. VN CAPM/FF3/FF5, GRS, alpha/t | PASS — ECONOMETRICS TEAM BASELINE | `outputs/vn_econometrics_baseline/` has 90 asset/model results, 30×22 Table 7-style values including alpha, beta, OLS t, HAC z and R²; three GRS results; HAC/VIF; HML spanning; and VN100/VNINDEX sensitivity. The LHS rule uses only June 2021 formation information. | No unfinished Step 7 calculation. Method definitions and limitations are documented in `docs/vn_econometrics_method_choices.md`. |

The original checklist's `Người phụ trách`, `Trạng thái`, and `Ghi chú` cells are blank; the PASS labels above are the Econometrics Team's audit status and have not been written into the user's original workbook. The Method Spec had already been submitted and was not changed in this implementation PR.

## Econometrics Team VN baseline result

| Model | N assets | T months | K factors | Mean absolute alpha (%/month) | Mean R² | GRS F | GRS p |
|---|---:|---:|---:|---:|---:|---:|---:|
| CAPM | 30 | 60 | 1 | 0.7006 | 0.3097 | 0.4837 | 0.9738 |
| FF3 | 30 | 60 | 3 | 0.7359 | 0.3683 | 0.7079 | 0.8211 |
| FF5 | 30 | 60 | 5 | 0.7923 | 0.4702 | 0.7727 | 0.7519 |

The Econometrics Team chose the 30 largest VN100 members by June 2021 formation market cap; that formation date precedes the 60-month return window. All 30 have all 60 returns; all 1,800 observations use the Factor Team's `close_eom` rule. Seven selected rows have a reported-vs-price return gap above one percentage point; none was removed. FF3 R² exceeds CAPM for all 30; FF5 R² is below FF3 for PDR.HM. FF5 uses `SMB_FF5`, so its RHS is not strictly nested in FF3. The maximum VN100-baseline RHS VIF is 1.6413.

The baseline uses VN100 MKT-RF derived from the matched monthly VN100 return series minus the Factor Team RF. The same 30 stocks, 60 months and remaining factors were run with VNINDEX MKT-RF: GRS F is 0.4708/0.7187/0.8216 for CAPM/FF3/FF5 under VNINDEX, compared with 0.4837/0.7079/0.7727 under VN100. Full alpha, R², p-values, and VIF comparisons are in `market_proxy_sensitivity.csv`.

## Econometrics Team method record

The baseline choices are recorded in `docs/vn_econometrics_method_choices.md`: formation-date top-30 universe; VN100 MKT with VNINDEX sensitivity; Factor Team RF from 1Y yield converted monthly; latest public statement by formation; lagged total market-cap factor weights; and price-derived returns with reported-return reconciliation. The source package does not include a one-month RF series. FF5 has 60 complete months, the five-year lower bound in the brief. The user ZIP hash and raw rebuild comparison are preserved above.

The submitted Method Spec is separate from the Step 7 computation and was left unchanged in this implementation.
