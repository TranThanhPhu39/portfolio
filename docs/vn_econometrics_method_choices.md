# Econometrics Team VN100 method baseline

The Econometrics Team sets the Step 7 baseline to match the assignment and available point-in-time data. The run uses a formation-date cohort, VN100 market return, the Factor Team's SMB/HML/RMW/CMA and RF series, and the common FF5 period. A VNINDEX run is included as a market-proxy sensitivity.

| Choice | Baseline definition | Rationale and audit evidence |
|---|---|---|
| LHS assets | 30 largest VN100 members by formation market capitalization at 2021-06-30; hold the selected cohort from 2021-07 through 2026-06. | The list is fixed from information available at formation, before the dependent-return window. All 30 selected stocks have all 60 monthly observations. The list and formation values are in `config/vn_econometrics_universe.csv`. The 30 assets are the checklist's allowed stock-level LHS. |
| Common sample | 60 month-end observations, 2021-07 to 2026-06, identical for CAPM, FF3, FF5, HAC, VIF, and GRS. | FF3 inputs exist for 96 months, but complete FF5 inputs exist for 60. Use the common 60-month intersection so models and GRS use identical rows. This meets the project brief's five-year lower bound. |
| CAPM | `Ri - RF = alpha + beta × MKT_RF + error`. | Raw stock returns are the LHS; `run_factor_regression()` subtracts the monthly RF once. |
| FF3 | Adds Factor Team `SMB` and `HML` to MKT_RF. | Use the factor series from the matched Factor Team monthly file. |
| FF5 | Adds `SMB_FF5`, `HML`, `RMW`, and `CMA` to MKT_RF. | Use the separate five-factor SMB series constructed by Factor Team. Use raw HML and label it HML; no HMLO series was supplied or constructed. |
| MKT | VN100 monthly index return from the matched `vn100_returns_clean.csv`, minus the Factor Team RF. | The project brief specifies the VN100 market portfolio. The source panel stores the VN100 monthly return consistently across ticker rows. The runner checks one unique VN100 value per month. A matched VNINDEX result is also reported in `market_proxy_sensitivity.csv`. |
| RF | Factor Team's annual 1Y government yield converted to an effective monthly decimal return. | The supplied package has 1Y/3Y/10Y series, not a one-month Treasury bill or one-month interbank series. The 1Y conversion is therefore the available baseline proxy; its tenor remains explicit in the report. |
| Factor formation and weights | June formation, July-to-June holding, lagged total market-cap weights; financial firms included. | Matches the Factor Team period pipeline. We do not add a free-float multiplier because the delivered Factor Team outputs use lagged total market capitalization. |
| Accounting information | Latest BCTC statement announced on or before the June formation date. | The source has announcement dates and the Factor Team audit flags no after-formation dates among the 800 formation rows. This quarterly point-in-time adaptation differs from requiring only fiscal year t-1; report it as the VN implementation. |
| LHS stock return | Use the Factor Team `return`: price-derived from consecutive `Close (EOM)` when available, with the reported return as fallback. | All 1,800 LHS observations have source `close_eom`. Seven selected rows differ from reported returns by more than one percentage point; the observations remain included and are identified in the Factor Team reconciliation. |
| HAC and VIF | OLS coefficients; Bartlett HAC with lag 12 and lag 6 sensitivity; VIF on each model's RHS factors. | The run exports OLS t statistics and HAC z statistics separately. No factor VIF exceeds 10. |
| GRS | Run one joint alpha test per model on all 30 selected stocks. | `T=60`, `N=30`, and the largest `K=5`; hence `T > N + K` and the FF5 denominator degrees of freedom are 25. |
| HML redundancy | Regress HML on MKT_RF, SMB_FF5, RMW, and CMA; report its intercept with OLS and HAC inference. | A direct auxiliary test of whether the HML average return is absorbed by the other FF5 factors. Interpret as a VN sample result, not the US paper's conclusion. |

## Baseline result files

`outputs/vn_econometrics_baseline/run_report.md` and `table5_style_summary.csv` summarize alpha, R², GRS, and p-values. `table7_style_assets.csv` reports alpha, factor betas, OLS t statistics, HAC z statistics, and R² for each stock and model. `market_proxy_sensitivity.csv` compares VN100 and VNINDEX under the same LHS, sample, RF, and other factors. `run_manifest.json` records source commit and input hashes.

The VN100-baseline GRS F/p-values are CAPM 0.4837/0.9738, FF3 0.7079/0.8211, and FF5 0.7727/0.7519. The same-sample VNINDEX sensitivity gives 0.4708/0.9779, 0.7187/0.8105, and 0.8216/0.6989 respectively. Full per-stock sensitivity outputs are in `outputs/vn_econometrics_market_sensitivity_vnindex/`.

The submitted Method Spec is separate from these calculations and was not modified in this implementation PR. This document records the Econometrics Team's chosen implementation and results.
