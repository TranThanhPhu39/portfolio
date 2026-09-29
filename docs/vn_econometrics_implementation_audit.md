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
| VN models | `scripts/run_vn_econometrics.py` | 90 OLS fits (30 assets × 3 models), 360 coefficient rows with HAC lag 12/6, 9 VIF rows, 3 GRS tests, one HML spanning regression, and Table 5/7-style outputs. All use the same 60 month ends from 2021-07 to 2026-06. |
| VN cross-check | Prior Factor Team smoke snapshot in the original checkout | The new runner's 90 alpha values, OLS t-statistics, R² values, and three GRS F/p pairs match the prior smoke run exactly for the same 30 tickers. |
| Explicit-universe CLI | `scripts/run_vn_econometrics.py --universe ...` | Executed with the exported 30-ticker list in a temporary output directory; produced the same models/GRS and labelled the sample as requiring review. |
| Raw factor rebuild | `scripts/build_vn_period_factors.py` with the user-supplied combined ZIP passed as both inputs | Rebuilt 96 factor months, 800 formation rows, and all 11 output CSVs without altering the archive. Eight CSVs matched the Factor Team commit byte-for-byte after newline normalization; the other three matched in shape/missingness with a maximum numeric gap of `4.44e-16`. |

The VM's pinned runtime used here is Python 3.12.14, pandas 2.2.0, numpy 1.26.0, scipy 1.13.0, statsmodels 0.14.0, openpyxl 3.1.5, and vnstock 3.5.0. `pytest` is absent from this runtime, so no pytest suite was run; the entry-point and result reconciliations above are the executed checks.

## Checklist status, Steps 1–7

| Step | Status | Evidence against the checklist output / DoD | Remaining action |
|---|---|---|---|
| 1. Understand the 25 LHS portfolios | PASS | `outputs/full_audit_steps1_6.md` maps the 25 Size×B/M columns to rows and columns; it identifies `SMALL LoBM` as the selected test LHS. | None for the test-data DoD. |
| 2. Generic CAPM/FF3/FF5 regression | PASS | `src/models/regressions.py` returns statsmodels results; CAPM/FF3/FF5 each print summaries on the 606-month sample. | None for the test-data DoD. |
| 3. Compare three models on one LHS | PASS | `outputs/step3_model_comparison.csv` reports alpha, t-stat, R² and N; R² is 0.6449 < 0.9171 < 0.9319 on the required US sample. | This ordering is not imposed on VN because FF3 and FF5 use different SMB series. |
| 4. Compare with Fama–French (2015) | PASS WITH LIMITATION | `outputs/step4_audit.md` and the Table 5/7 comparison CSVs report close test-sample results and disclose that the current LHS vintage is not proven to be the exact 2015 file. | Do not describe the comparison as an exact historical replication. |
| 5. GRS on all 25 LHS portfolios | PASS | `outputs/step5_grs_results.csv` contains GRS F and p-values for CAPM/FF3/FF5, with vintage sensitivity; the independent implementation agrees numerically. | None for the test-data DoD. |
| 6. Newey–West and VIF | PASS | `outputs/step6_hac_results.csv` contains lag 12 and lag 6; `outputs/step6_vif.csv` reports all factors below 10. | None for the test-data DoD. |
| 7. VN CAPM/FF3/FF5, GRS, alpha/t | TECHNICAL RUN PASS; FINAL SIGN-OFF PENDING | `outputs/vn_econometrics_provisional/` has 90 asset/model results, 30×22 Table 7-style values including alpha, beta, OLS t, HAC z and R², three GRS results, HAC/VIF and HML spanning. Raw ZIP rebuild reproduces the Factor Team inputs. | Group lead must approve the 30-asset LHS and current MKT/RF/accounting/weighting choices before this is called the final research result. |

The original checklist's `Người phụ trách`, `Trạng thái`, and `Ghi chú` cells for these rows are blank. The PASS labels above reflect repository evidence, not entries already approved in the workbook. The Method Spec is a separate deliverable: it remains unfilled as requested, and its current DOCX structure still differs from the supplied template.

## Current provisional VN result

| Model | N assets | T months | K factors | Mean absolute alpha (%/month) | Mean R² | GRS F | GRS p |
|---|---:|---:|---:|---:|---:|---:|---:|
| CAPM | 30 | 60 | 1 | 0.8215 | 0.2604 | 0.6572 | 0.8706 |
| FF3 | 30 | 60 | 3 | 0.7924 | 0.3704 | 0.5828 | 0.9238 |
| FF5 | 30 | 60 | 5 | 0.8071 | 0.4402 | 0.6035 | 0.9068 |

The selection is technical: 30 stocks with full common-period returns, ranked by total source-month coverage and ticker. All 1,800 selected asset-month returns come from the Factor Team's `close_eom` return rule. Eighty-six selected rows have a reported-vs-price return gap above one percentage point in the Factor Team audit column; no row was silently removed. FF3 R² exceeds or equals CAPM for all 30, while FF5 R² is below FF3 for HPG.HM, HSG.HM, and HVN.HM; FF5 uses `SMB_FF5`, so its RHS is not strictly nested in the FF3 RHS. No VIF exceeds 10.

## Pending before research sign-off

The project lead needs to approve the 30 test assets or portfolios and the Factor Team's current method choices: VNINDEX market proxy, effective monthly RF from 1Y yield, latest public accounting statement at June formation, total market-cap weighting, and price-derived returns. These differ from options in the supplied project brief. FF5 has 60 complete months; a longer FF5 period requires additional point-in-time OP/Inv inputs. The user-supplied combined ZIP now reproduces the versioned Factor Team output; it is held outside the Git checkout and must accompany a full raw-to-output handoff on another machine.

The separate Method Spec remains an unfilled form for the designated writer. Its formatting difference from the supplied template is a documentation follow-up, not an inference made by this runner.
