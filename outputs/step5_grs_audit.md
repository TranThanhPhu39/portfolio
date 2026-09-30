# Step 5: GRS joint-alpha test

## Inputs and alignment

The test uses all 25 value-weighted Size-B/M portfolio returns and the same FF3/FF5 factor sources as Step 4. The current input files contain 606 complete month-start observations from July 1963 through December 2013. RF is subtracted from every raw portfolio return; the published Mkt-RF series is already an excess-return factor and is not adjusted a second time.

## Method

The null is that all 25 intercepts are jointly zero. For each factor specification, the runner fits 25 OLS equations on the same dates, obtains the intercept vector and residual matrix, and evaluates:

`GRS = (T/N) * ((T-N-K)/(T-K-1)) * (alpha' Sigma_e^-1 alpha) / (1 + mean_f' Omega_f^-1 mean_f)`

Here `Sigma_e = E'E/(T-K-1)` is the unbiased residual covariance and `Omega_f` uses divisor `T-1`. The reference F distribution is `F(N, T-N-K)`. The p-value is computed with SciPy's upper-tail survival function. Positive-definite covariance matrices are checked with Cholesky factorization and solved without explicitly forming matrix inverses.

The finite-sample GRS reference assumes the standard joint normality and time-independence conditions for regression disturbances. It is the classical test; HAC/Newey-West adjustments are not part of this statistic and remain in Step 6.

An independent matrix-OLS path recomputes the equivalent statistic using the MLE residual covariance `E'E/T`. Every run must agree with the covariance-unbiased implementation before output is written. Across the saved runs, the maximum statistic gap is 5.773e-15 and the maximum alpha gap is 1.605e-17.

## Results

Table 5 Panel A's 2x3-factor GRS references are **3.62** for FF3 (`HML`) and **2.84** for FF5 (`HML RMW CMA`). The paper does not report row-level p-values; all p-values below are computed from the stated F distribution.

| Model | Variant | T | N | K | F numerator df | F denominator df | GRS | p-value | Independent GRS gap | Table 5 GRS | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CAPM | current CSV | 606 | 25 | 1 | 25 | 580 | 4.4246 | 1.79621e-11 | 2.66454e-15 | — | — |
| FF3 | current CSV | 606 | 25 | 3 | 25 | 578 | 3.5676 | 2.15799e-08 | 4.44089e-15 | 3.6200 | -0.0524 |
| FF5 | current CSV | 606 | 25 | 5 | 25 | 576 | 3.1204 | 7.80914e-07 | 3.9968e-15 | 2.8400 | 0.2804 |
| FF3 | July 2014 archive sensitivity | 606 | 25 | 3 | 25 | 578 | 3.5030 | 3.64406e-08 | 1.77636e-15 | 3.6200 | -0.1170 |
| FF3 | July 2015 archive sensitivity | 606 | 25 | 3 | 25 | 578 | 3.5036 | 3.62847e-08 | 3.55271e-15 | 3.6200 | -0.1164 |
| FF5 | July 2015 archive sensitivity | 606 | 25 | 5 | 25 | 576 | 2.9073 | 4.12386e-06 | 5.77316e-15 | 2.8400 | 0.0673 |

Current-source FF3 differs from its Table 5 reference by -0.0524; current-source FF5 differs by +0.2804. The July 2015 FF5 factor sensitivity yields GRS 2.9073, a gap of +0.0673 from Table 5; its LHS is still the current local file. CAPM is included as a joint test but has no matching Table 5 GRS reference. Archive rows are factor-vintage sensitivities using the current local portfolio file, not full 2015-vintage replications.

## Input fingerprints

Current CSV SHA-256 values:

- `25_portfolios_size_bm.csv`: `8e5c97c32979efef10dfa07f2446d336d356bee0b5cc1232d6c59f6edee54b91`
- `ff3_factors_monthly.csv`: `490fa48b0a8e94b3b965576c0a203ccf5c70bf30cd25848968de47a996a6cce0`
- `ff5_factors_monthly.csv`: `1edb98f0db0a2ea056cec38fefa5e7b539eceae09679d2af07450a6795bef98f`

Archive ZIP SHA-256 values:

- `ff3_july2014.zip`: `e778483cfcf4041821601433a5e470fd4b255082fa0355b35f70307a515f68e9`
- `ff3_july2015.zip`: `d40f89a404b677d1bb071b1554acaa71ec50c7d50b46b1c2037e55230b0d1b4c`
- `ff5_july2015.zip`: `c50321fcd2e82b8a2350af3b14fb55cb8c4f17b2c82cc27eb598b3942ccb411f`

- All locally available archive sensitivities were run.
