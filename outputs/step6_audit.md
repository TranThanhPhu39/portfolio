# Step 6: HAC and VIF diagnostics

## Inputs and specification

HAC inference is calculated for `SMALL LoBM`, the same LHS used in Steps 2-4, on the complete July 1963–December 2013 sample (606 months). CAPM and FF3 use `ff3_factors_monthly.csv`; FF5 uses `ff5_factors_monthly.csv`. RF is subtracted from the raw portfolio return and is not an RHS factor. VIF is computed from each model's RHS factors on the same source/sample, with an intercept in its auxiliary design matrix; RF and the intercept are not reported as VIF targets.

HAC uses the Bartlett kernel, small-sample correction, and asymptotic-normal inference (`use_t=False`). Lag 12 is the primary monthly bandwidth; lag 6 is included as a sensitivity run. The HAC covariance changes standard errors and inference, not OLS coefficients. Extreme-tail p-values that underflow in standard floating-point output retain their finite log p-value in the full CSV.

## Newey-West results

The table reports the intercept and its standard error in percent per month at the primary 12-lag setting. The complete coefficient-level CSV retains regression-scale coefficients and records their units; it includes both lags.

The OLS alpha and t-statistic at lag 12 are cross-checked against the Step 3 comparison before output is written. Maximum Step 3 alpha gap is 3.182e-13 in decimal returns; maximum OLS t-statistic gap is 4.137e-10.

The HAC covariance is separately recomputed from the Bartlett weighted score products. Its maximum difference from statsmodels is 1.258e-17. VIFs are also checked against the auxiliary-regression definition; the maximum difference is 8.882e-16.

| Model | Factor source | T | Alpha OLS (%/month) | OLS t | HAC SE (%/month), lag 12 | z HAC | HAC p-value |
|---|---|---|---|---|---|---|---|
| CAPM | ff3_factors_monthly.csv | 606 | -0.4479 | -2.2977 | 0.2346 | -1.9092 | 0.0562402 |
| FF3 | ff3_factors_monthly.csv | 606 | -0.4941 | -5.1490 | 0.1116 | -4.4283 | 9.50003e-06 |
| FF5 | ff5_factors_monthly.csv | 606 | -0.2747 | -3.0569 | 0.0849 | -3.2362 | 0.00121153 |

The intercept's significance sensitivity to the two bandwidths is:

| Model | z lag 12 | p lag 12 | z lag 6 | p lag 6 | Reject 5% at 12 | Reject 5% at 6 | Decision changes |
|---|---|---|---|---|---|---|---|
| CAPM | -1.9092 | 0.0562402 | -2.0643 | 0.0389884 | No | Yes | Yes |
| FF3 | -4.4283 | 9.50003e-06 | -4.7361 | 2.17889e-06 | Yes | Yes | No |
| FF5 | -3.2362 | 0.00121153 | -3.2248 | 0.00126043 | Yes | Yes | No |

## VIF results

Project threshold: VIF > 10. The installed statsmodels 0.14.0 documentation also flags >5 as a common caution reference. Values are reported without altering factors.

| Model | Factor | VIF | >5 reference | >10 project flag | T |
|---|---|---|---|---|---|
| CAPM | Mkt-RF | 1.0000 | No | No | 606 |
| FF3 | Mkt-RF | 1.1510 | No | No | 606 |
| FF3 | SMB | 1.1183 | No | No | 606 |
| FF3 | HML | 1.0999 | No | No | 606 |
| FF5 | Mkt-RF | 1.3118 | No | No | 606 |
| FF5 | SMB | 1.1932 | No | No | 606 |
| FF5 | HML | 2.0044 | No | No | 606 |
| FF5 | RMW | 1.2236 | No | No | 606 |
| FF5 | CMA | 2.2595 | No | No | 606 |

Maximum VIF: 2.2595. No factor VIF exceeds the project threshold of 10. Values above the statsmodels >5 reference: none.

## Audit conclusion

The runner validates the three input files, fits all three Step 3 models on T=606 observations, generates 24 HAC coefficient rows (three models, intercept plus RHS factors, two lag settings), and generates 9 VIF rows. Coefficients from the HAC results are checked against their OLS values before output is written. Bandwidth sensitivity changes the CAPM alpha decision at 5%; report both lags. No factor VIF exceeds the project threshold of 10.

Current CSV SHA-256 values:

- `25_portfolios_size_bm.csv`: `8e5c97c32979efef10dfa07f2446d336d356bee0b5cc1232d6c59f6edee54b91`
- `ff3_factors_monthly.csv`: `490fa48b0a8e94b3b965576c0a203ccf5c70bf30cd25848968de47a996a6cce0`
- `ff5_factors_monthly.csv`: `1edb98f0db0a2ea056cec38fefa5e7b539eceae09679d2af07450a6795bef98f`
