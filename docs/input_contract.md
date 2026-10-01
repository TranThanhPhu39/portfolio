# Backtest input contract

Runner chung: `python run_backtest.py --config config/example.json`.
Paths inside a config resolve relative to that config file. Output folders must be new.

| File | Required columns | Meaning |
|---|---|---|
| returns | date,ticker,return | Monthly simple decimal returns, not log returns or percent values |
| risk_free | date,rf_return | Monthly simple decimal risk-free proxy |
| benchmark | date,return | Monthly simple decimal benchmark return |
| membership (dynamic only) | date,ticker,member | Explicit `true`/`false` or `1`/`0` for every month/ticker pair |
| monthly prices for prepare_prices.py | date,ticker,adjusted_price | Positive month-end adjusted prices on a declared consistent basis |

Dates must be calendar-month-end labels, sorted, with consecutive months. One observation per month/key. Fixed-universe returns must be complete and finite. Dynamic returns may be sparse only for assets that are not held; membership itself may never be missing or ambiguous. The loaders reject duplicate tickers, forward fill, returns <= -1, silent month removal and missing held-asset returns.

`config/example.json` uses included seeded fixtures and is executable. `config/research.template.json` and `config/dynamic.template.json` intentionally contain placeholders and must be filled before a research run; they are not executable research results.

For a generic dynamic CSV run, set `universe_mode` to `dynamic` and provide `membership` as shown in `config/dynamic.template.json`. The specialized VN entry point remains `run_vn100.py --input <folder> --output local_runs/vn_01 --return-basis provided --rf-basis annual_effective_percent`; it converts the group's period files before calling the same dynamic engine. RF conversion is explicit and source assumptions remain unresolved.
