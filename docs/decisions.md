# Backtest implementation decisions

- Distinguish executable demo, 30-stock integration test, and exploratory Vietnam run. Successful code execution does not certify research data.
- Historical arithmetic means, sample covariance plus ridge (default 1e-8); no fitted FF model in expected returns.
- Long-only fully invested MinVariance, MaxSharpe and EqualWeight. Explicit errors instead of silent optimizer fallback.
- 24 months ending at t-2, one full implementation-lag month, monthly rebalance before month t returns.
- Fees on both purchases and sales, initial purchase charged, no terminal liquidation. Scenarios 0, 0.0015, 0.0025, 0.0035; same targets in all scenarios.
- Include initial wealth in drawdown peak. Compare on identical dates within each run; benchmark has no simulated trading fee.
- Dynamic universe: require full past window, sell exiting constituents, reject missing held returns. Eligibility and exclusions exported.
- Missing/ambiguous VN source definitions are recorded, not guessed away. RF annual-effective conversion is a documented scenario, not independent verification of provider quoting convention.
- Keep factor/econometrics files and results at the repository root intact. Backtest local reruns write `local_runs/`; the standalone package remains independently runnable.
