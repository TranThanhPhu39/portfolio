# Backtest input contract

Fixed-universe runner: `python run_backtest.py --config config/example.json`.
Paths inside a config resolve relative to that config file. Output folders must be new.

| File | Required columns | Meaning |
|---|---|---|
| returns | date,ticker,return | Monthly simple decimal returns, not log returns or percent values |
| risk_free | date,rf_return | Monthly simple decimal risk-free proxy |
| benchmark | date,return | Monthly simple decimal benchmark return |
| monthly prices for prepare_prices.py | date,ticker,adjusted_price | Positive month-end adjusted prices on a declared consistent basis |

Dates must be calendar-month-end labels, sorted, with consecutive months. One observation per month/key. Fixed-universe returns must be complete and finite; no duplicate tickers, forward fill, returns <= -1, silent month removal or missing held-asset returns.

`config/example.json` uses included seeded fixtures and is executable. `config/research.template.json` intentionally contains placeholders and must be filled before a research run; it is not an executable research result.

Dynamic VN entry point: `run_vn100.py --output local_runs/vn_01 --return-basis provided --rf-basis annual_effective_percent`. It reads only bundled period files under `back_test_hoan_chinh/data/vn100_periods`. These are percent-return source files; RF conversion is explicit and source assumptions remain unresolved. See `back_test_hoan_chinh/METHOD_SPEC.md` for eligibility, RF, price discrepancies and research limitations. Do not send a sparse changing-universe panel to the fixed runner.
