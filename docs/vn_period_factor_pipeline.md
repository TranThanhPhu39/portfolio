# VN100 period factor pipeline

The pipeline reads the two supplied ZIP archives directly. It does not
extract, overwrite, or otherwise modify the raw files.

## Run

The builder requires two source archives: one with the period CSVs at the ZIP
root, and one with the master workbook and RF workbook at the ZIP root. Supply
their local paths as its two positional arguments. The originally supplied
archives are not tracked in this repository; the generated CSVs below are.

```powershell
.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py PERIOD_ARCHIVE.zip MASTER_ARCHIVE.zip
```

Use `--help` to see all configuration options.

## Default methodology

- Form portfolios at the end of June and hold them from July in year `t`
  through June in year `t+1`.
- Use the VN100 membership supplied for each June formation date.
- Weight portfolio returns by lagged monthly market capitalization.
- Use the latest financial statement announced on or before the formation
  date. Never use information announced after formation.
- Convert the one-year government yield from annual percent to an effective
  monthly decimal risk-free return.
- Use VNINDEX as the market proxy.
- Exclude annual holding periods that do not contain all 12 market months.
- Recompute monthly stock returns from consecutive `Close (EOM)` observations.
  Preserve the supplied return for reconciliation and use it only when the
  preceding monthly close is unavailable.
- Flag extreme and materially discrepant returns instead of silently deleting
  or winsorizing observations.

The current output uses the latest financial statement announced by June
formation, without requiring that the accounting period be fiscal year `t-1`.
The output also uses VNINDEX as MKT, a converted 1Y government yield as RF,
and total market capitalization rather than free-float-adjusted weights.
These definitions differ from options described in the project brief and must
be named when reporting results.

## Outputs

Results are written to `outputs/vn_period_factors/`.

- `vn100_factors_monthly.csv`: monthly MKT-RF, SMB, HML, SMB_FF5, RMW, CMA,
  RF, and market returns.
- `vn100_factor_summary.csv`: descriptive statistics and t-statistics.
- `vn100_factor_correlations.csv`: factor correlations.
- `vn100_formation_audit.csv`: point-in-time accounting match, eligibility,
  and exclusion reason for every formation security.
- `vn100_group_assignments.csv`: portfolio assignment for every eligible
  security.
- `vn100_group_counts.csv`: security counts in each portfolio.
- `vn100_returns_clean.csv`: normalized decimal return panel used by the
  pipeline, including both reported and price-derived returns.
- `vn100_return_reconciliation.csv`: observations with a return discrepancy
  above one percentage point, a missing price return, or a return above 100%.
- `vn100_data_quality.csv`: period-level eligibility and outlier counts.
- `vn100_periods_audit.csv`: supplied schedule and completeness assessment.
- `vn100_fundamental_event_conflicts.csv`: duplicated announcement events
  whose accounting values conflict and therefore require review.
