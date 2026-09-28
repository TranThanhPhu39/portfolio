# Archived audit before Step 6: Steps 1-5

This is the checkpoint recorded before Step 6. For the completed Steps 1-6 result, see `../full_audit_steps1_6.md`.

## Verdict

**Steps 1-5 pass their checkable inputs, outputs, and completion criteria.** No Step 6 or Step 7 analysis was run in this audit. The results below were checked against the project data and independently recomputed. This confirms the implemented test pipeline; it does not claim an exact 2015-vintage replication because the current local 25-portfolio file has no vintage metadata and a matching historical LHS snapshot was not recovered.

## Shared test inputs

| File | Verified dimensions | Date sample | Checks |
|---|---:|---|---|
| `data/test/kenneth_french/25_portfolios_size_bm.csv` | 606 × 25 | 1963-07 through 2013-12 | No duplicate dates, missing cells, or non-finite values; value-weighted return series in decimal units |
| `data/test/kenneth_french/ff3_factors_monthly.csv` | 606 × 4 | 1963-07 through 2013-12 | Mkt-RF, SMB, HML, RF; no duplicate dates, missing cells, or non-finite values |
| `data/test/kenneth_french/ff5_factors_monthly.csv` | 606 × 6 | 1963-07 through 2013-12 | Mkt-RF, SMB, HML, RMW, CMA, RF; no duplicate dates, missing cells, or non-finite values |

The data helper selects table 0 from the Kenneth French `25_Portfolios_5x5` response and converts percent returns to decimals. FF3 and FF5 are separate factor files; their SMB series are not interchangeable. The current CSV hashes are recorded in `step4_audit.md` and `step5_grs_audit.md`.

## Step-by-step completion

### Step 1: Identify the 25 LHS portfolios — PASS

Conceptually arrange the 25 portfolio columns as a 5×5 grid: size quintiles form the rows (ME1/Small, ME2, ME3, ME4, ME5/Big); book-to-market quintiles form the columns (BM1/Low, BM2, BM3, BM4, BM5/High). The CSV itself is a date-by-portfolio table.

- Small: `SMALL LoBM`, `ME1 BM2`, `ME1 BM3`, `ME1 BM4`, `SMALL HiBM`.
- ME2: `ME2 BM1` through `ME2 BM5`.
- ME3: `ME3 BM1` through `ME3 BM5`.
- ME4: `ME4 BM1` through `ME4 BM5`.
- Big: `BIG LoBM`, `ME5 BM2`, `ME5 BM3`, `ME5 BM4`, `BIG HiBM`.

The header contains exactly 25 unique portfolio columns. The selected first LHS for Steps 2-4 is `SMALL LoBM`.

### Step 2: Generic factor regression — PASS

`src/models/regressions.py` exposes `run_factor_regression()` for raw decimal portfolio returns, a factor DataFrame, selected factor columns, and RF. It date-aligns inputs, subtracts RF from the LHS, adds an intercept, verifies numeric finite data and full design rank, and returns a statsmodels OLS results object.

The audit called `.summary()` on the FF5 regression for `SMALL LoBM`; it returned an OLS summary without error with 606 observations. The fitted FF5 alpha was -0.274699% per month, t(alpha) -3.056885, and R² 0.931853.

### Step 3: CAPM, FF3, FF5 comparison — PASS

All three models ran for `SMALL LoBM` on the same 606-month sample. CAPM and FF3 use the FF3 factor file; FF5 uses the FF5 factor file.

| Model | Alpha (%/month) | t(alpha) | R² | N |
|---|---:|---:|---:|---:|
| CAPM | -0.447854 | -2.297717 | 0.644925 | 606 |
| FF3 | -0.494139 | -5.149019 | 0.917052 | 606 |
| FF5 | -0.274699 | -3.056885 | 0.931853 | 606 |

The stated R² criterion passes on the observed sample: 0.644925 < 0.917052 < 0.931853. Since the official FF3 and FF5 SMB series differ, strict R² growth is observed here, not guaranteed for every sample.

### Step 4: Compare with Fama-French (2015) — PASS, vintage limitation recorded

Table 7 Panel A's Small/Low B/M FF3 reference is alpha -0.49% per month and t(alpha) -5.18. The current-factor result is -0.494139 and -5.149019. Table 7 Panel B's FF5 reference is -0.29 and -3.31; the current FF5 result is -0.274699 and -3.056885. Reconstructing HML^O produced the same FF5 alpha, t-statistic, and R² as raw HML within numerical tolerance.

For Table 5 Panel A, the 25-portfolio mean absolute alpha and mean-absolute-alpha/deviation ratio were independently recomputed:

| Model | Own mean absolute alpha (%/month) | Table 5 | Own ratio | Table 5 |
|---|---:|---:|---:|---:|
| FF3 | 0.097856 | 0.102 | 0.528523 | 0.54 |
| FF5 | 0.093856 | 0.094 | 0.506920 | 0.50 |

The July 2015 FF5 factor archive with the current LHS moves the SMALL LoBM alpha to -0.289222% per month, which rounds to the Table 7 value; its t-statistic is -3.245427. The current FF5 GRS at Step 5 is also closer to the Table 5 value when using the July 2015 FF5 factors. These are factor-vintage sensitivity results only. The matching 2015 LHS vintage remains unverified.

Table 5/7 contains no CAPM comparison value. Table 5 p-values are not listed; only the group's computed p-values are reported in Step 5.

### Step 5: Joint GRS test — PASS, vintage limitation recorded

`src/models/grs_test.py` implements the joint test for all 25 alphas. It uses the same complete sample for every LHS, RF-adjusted returns, unbiased residual covariance with divisor T-K-1, factor covariance with divisor T-1, Cholesky checks/solves, and the exact upper tail of F(25, T-25-K).

| Model/source | K | GRS | p-value | Table 5 reference |
|---|---:|---:|---:|---:|
| CAPM/current FF3 | 1 | 4.424553 | 1.7962e-11 | None in Table 5 |
| FF3/current CSV | 3 | 3.567626 | 2.1580e-08 | 3.62 |
| FF5/current CSV | 5 | 3.120385 | 7.8091e-07 | 2.84 |
| FF5/July 2015 factor archive, current LHS | 5 | 2.907306 | 4.1239e-06 | 2.84 |

The FF3 reference gap is -0.052374; the current FF5 gap is +0.280385; the July 2015 FF5 factor sensitivity gap is +0.067306. All model p-values are below 0.05 under the classical GRS assumptions. Table 5 does not publish row-level p-values.

An independent matrix-OLS calculation using the equivalent MLE residual covariance form agrees with the main GRS implementation: maximum statistic gap 1.243e-14 and maximum alpha gap 1.542e-17 across all current and archive runs. The Step 5 GRS alpha averages also match the Step 4 Table 5 alpha summaries within 5e-12.

## Environment and verification notes

- The active project environment reports pandas 2.2.0, NumPy 1.26.0, SciPy 1.13.0, and statsmodels 0.14.0.
- The analysis runners for Steps 3, 4, and 5 completed successfully. No Step 6 tests or VN-data analysis were run.
- `git diff --check` exits successfully; it reports only working-tree LF/CRLF conversion advisories.
- Pandas prints a future PyArrow dependency warning for pandas 3.0; the pinned pandas 2.2.0 analyses completed.

## Artifacts

- Step 3: `scripts/compare_factor_models.py`, `outputs/step3_model_comparison.csv`.
- Step 4: `scripts/compare_to_fama_french_2015.py`, `outputs/step4_table7_comparison.csv`, `outputs/step4_table5_panel_a_comparison.csv`, `outputs/step4_audit.md`.
- Step 5: `src/models/grs_test.py`, `scripts/run_grs_test.py`, `outputs/step5_grs_results.csv`, `outputs/step5_grs_audit.md`.
