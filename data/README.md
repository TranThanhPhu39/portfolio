# Data map

The folder follows the project brief's `data/` location. It separates reproducibility inputs from historical reference files.

## Test data

### `test/kenneth_french/`

- [`25_portfolios_size_bm.csv`](test/kenneth_french/25_portfolios_size_bm.csv): the 25 value-weighted Size-B/M portfolios used as LHS returns for the U.S. test regressions and GRS test.
- [`ff3_factors_monthly.csv`](test/kenneth_french/ff3_factors_monthly.csv): monthly Mkt-RF, SMB, HML, and RF for CAPM and FF3.
- [`ff5_factors_monthly.csv`](test/kenneth_french/ff5_factors_monthly.csv): monthly Mkt-RF, SMB, HML, RMW, CMA, and RF for FF5.
- The saved test sample has 606 monthly observations from 1963-07 through 2013-12. Returns and factors are stored as decimals.
- FF3 and FF5 are kept in separate files because their SMB series are not interchangeable.

### `test/us_factor_logic/`

- [`us_test_prices.csv`](test/us_factor_logic/us_test_prices.csv): U.S. sample prices for exercising the Factor Team's portfolio-sort code.
- [`us_test_characteristics.csv`](test/us_factor_logic/us_test_characteristics.csv): synthetic size and book-to-market proxies for exercising sorting logic.
- The synthetic characteristics are test fixtures only. They are not empirical inputs and must not be used as Vietnam factor data.

### `test/factor_demo/`

- A separate 30-stock US demonstration snapshot contributed by Factor Team. `scripts/run_us_factor_demo.py` reads these files and writes `outputs/factor_demo/`.
- The demonstration uses synthetic profitability and investment characteristics. Do not use it for Vietnam regressions.

## Processed Vietnam inputs

The Factor Team's matched decimal return panel and monthly factors are versioned at `outputs/vn_period_factors/vn100_returns_clean.csv` and `outputs/vn_period_factors/vn100_factors_monthly.csv`. The econometrics runner reads that pair, records their SHA-256 hashes, and exports a 60-month comparison sample. Raw source archives used by the Factor Team's builder are separate inputs and are not included in this repository snapshot.

## Historical references

[`reference/kenneth_french/vintage_2014/`](reference/kenneth_french/vintage_2014/) and [`vintage_2015/`](reference/kenneth_french/vintage_2015/) contain official historical factor archives used for sensitivity comparisons. They support a historical factor-vintage check; they do not establish that the local 25-portfolio LHS file is the exact 2015 vintage.

## Rebuild

Run `scripts/get_test_data.py` from the repository root. It refreshes the current factor, portfolio, and U.S. sample CSVs. It does not download or overwrite the committed historical archives.
