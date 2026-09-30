# Full audit record: Steps 1-6

## Overall verdict

**Steps 1-6 pass their stated, checkable completion criteria on the current test dataset.** Inputs, outputs, and cross-step consistency have been rechecked. At the time this audit was written, Step 7 had not run. The Econometrics Team later selected a June 2021 formation-date VN baseline and ran Step 7; evidence is in [`vn_econometrics_baseline/run_report.md`](vn_econometrics_baseline/run_report.md).

The work uses the current local 25-portfolio LHS vintage. A matching 2015 vintage of the LHS portfolio file has not been established, so the Fama-French comparisons are approximate comparisons, not an exact historical replication. The vintage limitation is recorded in the Step 4 and Step 5 audit reports.

## Shared inputs

| Input | Verified shape | Sample | Result |
|---|---:|---|---|
| `data/test/kenneth_french/25_portfolios_size_bm.csv` | 606 × 25 | 1963-07 to 2013-12 | Unique dates and columns; no missing or non-finite values |
| `data/test/kenneth_french/ff3_factors_monthly.csv` | 606 × 4 | 1963-07 to 2013-12 | Mkt-RF, SMB, HML, RF; complete and finite |
| `data/test/kenneth_french/ff5_factors_monthly.csv` | 606 × 6 | 1963-07 to 2013-12 | Mkt-RF, SMB, HML, RMW, CMA, RF; complete and finite |

The data helper reads table 0 for the value-weighted 25 portfolios and converts percent returns to decimals. FF3 and FF5 factors come from separate files because their SMB series are not interchangeable.

## Completion audit

### Step 1 — 25 LHS portfolios: PASS

The 25 portfolio columns form a conceptual Size × B/M grid. Size rows are ME1/Small, ME2, ME3, ME4, ME5/Big. B/M columns are BM1/Low through BM5/High.

- Small: `SMALL LoBM`, `ME1 BM2`, `ME1 BM3`, `ME1 BM4`, `SMALL HiBM`.
- ME2, ME3, ME4: each has BM1 through BM5.
- Big: `BIG LoBM`, `ME5 BM2`, `ME5 BM3`, `ME5 BM4`, `BIG HiBM`.

The selected Step 2-4 LHS is `SMALL LoBM`.

### Step 2 — generic factor regression: PASS

`src/models/regressions.py` implements `run_factor_regression()`. It aligns dates, subtracts RF from the raw decimal LHS, adds an intercept, validates finite numeric inputs and design rank, and returns statsmodels OLS results.

The FF5 `SMALL LoBM` regression generated `model.summary()` without error, with 606 observations. Alpha was -0.274699% per month, t(alpha) -3.056885, and R² 0.931853.

### Step 3 — CAPM, FF3, FF5: PASS

All three regressions used `SMALL LoBM` and N=606. CAPM/FF3 use the FF3 factor file; FF5 uses the FF5 factor file.

| Model | Alpha (%/month) | t(alpha) | R² | N |
|---|---:|---:|---:|---:|
| CAPM | -0.447854 | -2.297717 | 0.644925 | 606 |
| FF3 | -0.494139 | -5.149019 | 0.917052 | 606 |
| FF5 | -0.274699 | -3.056885 | 0.931853 | 606 |

R² passes the required observed ordering: 0.644925 < 0.917052 < 0.931853. Since FF3 and FF5 use different official SMB definitions, this ordering is verified on this sample and is not treated as a mathematical guarantee for every sample.

### Step 4 — comparison with Fama-French (2015): PASS, vintage limitation recorded

Table 7 Panel A's Small/Low B/M FF3 reference is alpha -0.49% per month and t(alpha) -5.18. The current result is -0.494139 and -5.149019. Table 7 Panel B's FF5 reference is -0.29 and -3.31; the current result is -0.274699 and -3.056885. Reconstructing HML^O leaves the FF5 alpha, t-statistic and R² unchanged within numerical tolerance.

Table 5 Panel A was compared at its aggregate level using all 25 portfolios:

| Model | Own mean absolute alpha (%/month) | Table 5 | Own alpha/deviation ratio | Table 5 |
|---|---:|---:|---:|---:|
| FF3 | 0.097856 | 0.102 | 0.528523 | 0.54 |
| FF5 | 0.093856 | 0.094 | 0.506920 | 0.50 |

The July 2015 FF5 factor archive with the current LHS moves the SMALL LoBM alpha to -0.289222% per month, which rounds to Table 7's -0.29. Its t-statistic is -3.245427. This is a factor-vintage sensitivity run, not a full 2015-vintage reconstruction of the LHS.

### Step 5 — GRS on all 25 portfolios: PASS, vintage limitation recorded

`src/models/grs_test.py` tests the joint null that all 25 intercepts are zero. Every model uses the same complete sample. The finite-sample F statistic uses the unbiased residual covariance divisor T-K-1, factor covariance divisor T-1, Cholesky solves, and the upper-tail F survival probability.

| Model/source | K | GRS | p-value | Table 5 GRS |
|---|---:|---:|---:|---:|
| CAPM/current FF3 | 1 | 4.424553 | 1.7962e-11 | Not reported |
| FF3/current CSV | 3 | 3.567626 | 2.1580e-08 | 3.62 |
| FF5/current CSV | 5 | 3.120385 | 7.8091e-07 | 2.84 |
| FF5/July 2015 factor archive, current LHS | 5 | 2.907306 | 4.1239e-06 | 2.84 |

An independent matrix-OLS implementation using the equivalent MLE residual covariance agrees: the maximum GRS gap is 1.243e-14 and the maximum alpha gap is 1.542e-17. Table 5 does not publish row-level p-values; the reported p-values are computed from the stated F distribution. The current FF5 GRS differs from the reference by +0.280385; the July 2015 factor sensitivity reduces the gap to +0.067306 while retaining the current LHS.

### Step 6 — HAC and VIF: PASS

HAC inference was calculated for `SMALL LoBM` on all 606 months. It uses Bartlett weights, small-sample correction, asymptotic-normal inference (`use_t=False`), maxlags 12 as the primary monthly bandwidth and maxlags 6 as a sensitivity run. Coefficients were checked against Step 3; only inference changes. The OLS alpha gap from the Step 3 CSV is 3.182e-13 decimal returns and the OLS t-stat gap is 4.137e-10, consistent with stored CSV rounding.

| Model | HAC SE alpha (%/month), lag 12 | z-HAC | p-HAC |
|---|---:|---:|---:|
| CAPM | 0.2346 | -1.9092 | 0.0562402 |
| FF3 | 0.1116 | -4.4283 | 9.50003e-06 |
| FF5 | 0.0849 | -3.2362 | 0.00121153 |

CAPM's 5% inference changes with the lag setting: p=0.0562402 at lag 12 and p=0.0389884 at lag 6. FF3 and FF5 remain below 0.05 at both lags. Both lag results and log p-values for extreme tails are preserved in the HAC CSV.

VIF was calculated for every RHS factor by model, with an intercept in each auxiliary design and RF excluded. The maximum VIF is **2.2595** for FF5 CMA; no factor exceeds the project threshold of 10 or the statsmodels 5-point caution reference. Independent Bartlett-sandwich and auxiliary-regression calculations agree with the generated HAC covariance and VIF results; maximum gaps are 2.602e-17 and 4.441e-16, respectively.

The recorded maximum differences are 2.602e-17 for the HAC covariance versus the independent Bartlett-sandwich calculation, 4.441e-16 for VIF versus the independent auxiliary-regression calculation, 3.182e-13 for Step 3 versus Step 6 decimal alpha, and 4.137e-10 for their OLS t-statistics (the latter comes from the Step 3 CSV serialization).

## Source-level audit map

The active Python source was reviewed by function and control-flow block; all listed modules compile, and the end-to-end runners for Steps 3-6 execute.

| Source | Code blocks reviewed | Audit focus |
|---|---|---|
| `scripts/get_test_data.py` | Kenneth French data retrieval | FF3/FF5 datasets, P25 table 0 value-weighted returns, date cut and percent-to-decimal conversion |
| `src/models/regressions.py` | lines 13-33 date normalization; 35-102 `run_factor_regression` | Date types, duplicates, RF subtraction, intercept, design rank, finite values, statsmodels output |
| `scripts/compare_factor_models.py` | lines 21-28 model/source constants; 30-112 alignment and fits; 115-135 output | Factor-file assignment, 606-date sample, alpha/t/R², increasing-R² guard |
| `scripts/compare_to_fama_french_2015.py` | lines 54-132 CSV/archive parsing and HML^O; 134-245 fit/summary helpers; 247-465 orchestration; 467-506 output | Table 7 cell mapping, Table 5 aggregate stats, units, vintage and hashes |
| `src/models/grs_test.py` | lines 15-28 result type; 30-200 `grs_test` | Input validation, alignment, 25 OLS residuals, covariance divisors, F degrees, Cholesky and upper-tail p-value |
| `scripts/run_grs_test.py` | lines 79-137 input validation; 139-180 independent MLE formula; 182-237 execution checks; 276-447 output/report | CAPM/FF3/FF5 sources, archive sensitivities, Table 5 references and fingerprints |
| `src/models/diagnostics.py` | lines 18-28 result type; 30-101 HAC; 103-148 VIF | HAC settings, coefficient invariance, VIF design and edge handling |
| `scripts/run_step6_diagnostics.py` | lines 38-133 input and independent formula checks; 134-152 formatting; 154-462 orchestration; 464-483 CLI | 606-date sample, lags, Step 3 linkage, VIF flags, report and outputs |

No TODO or NotImplemented placeholder was found in these active files. GRS and HAC/VIF runners include independent formula checks and stop before saving if those checks fail.

## Environment and final checks

- Python environment versions verified: pandas 2.2.0, NumPy 1.26.0, SciPy 1.13.0, statsmodels 0.14.0.
- Runners for Steps 3-6 completed. Step 2 `summary()` and Step 3/4/5/6 outputs were checked against the same 606-month inputs.
- Markdown tables in the audit reports were checked for consistent row structure.
- `git diff --check` exits successfully; only LF/CRLF conversion advisories remain.
- Pandas prints a future PyArrow dependency warning for pandas 3.0; it does not affect the pinned pandas 2.2.0 calculations.

## Audit artifacts

- Step 3: `outputs/step3_model_comparison.csv`.
- Step 4: `outputs/step4_table7_comparison.csv`, `outputs/step4_table5_panel_a_comparison.csv`, `outputs/step4_audit.md`.
- Step 5: `outputs/step5_grs_results.csv`, `outputs/step5_grs_audit.md`.
- Step 6: `outputs/step6_hac_results.csv`, `outputs/step6_vif.csv`, `outputs/step6_audit.md`.
