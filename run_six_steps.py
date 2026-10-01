"""Run the six checklist stages on reproducible synthetic MONTHLY prices."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from src.portfolio.prices import load_prices
from src.portfolio.markowitz import estimate, solve, frontier, portfolio_stats, optimizer_factory
from src.portfolio.sharpe_comparison import export_sharpe_comparison
from src.backtest.walk_forward import run_cost_scenarios
from src.backtest.performance import comparison_table, fee_crossings
from src.backtest.reporting import export_report
from src.backtest.charts import svg_plot


def run(output, lookback=24, ridge=1e-8):
    out = Path(output)
    if out.exists():
        raise FileExistsError('Choose a new output directory; previous results are preserved')
    out.mkdir(parents=True)
    rng = np.random.default_rng(20260928)
    dates = pd.date_range('2017-01-31',periods=85,freq='ME')
    common = rng.normal(.005,.035,84)
    raw_returns = common[:,None] + rng.normal(.002,.025,(84,4))
    prices = pd.DataFrame(np.vstack([np.full(4,100.),100*np.cumprod(1+raw_returns,axis=0)]),
                          index=dates,columns=['SIM_A','SIM_B','SIM_C','SIM_D'])
    prices.rename_axis('date').reset_index().melt(id_vars='date',var_name='ticker',value_name='adjusted_price').to_csv(out/'01_SYNTHETIC_prices.csv',index=False)
    _, returns = load_prices(out/'01_SYNTHETIC_prices.csv')
    returns.to_csv(out/'01_monthly_returns.csv')
    (out/'01_validation.json').write_text(json.dumps({'synthetic':True,'price_rows':len(prices),'return_rows':len(returns),'assets':4,'missing':int(returns.isna().sum().sum()),'adjustment':'Simulated; no real corporate actions'}),encoding='utf-8')
    rf = pd.Series(.002,index=returns.index)
    benchmark = pd.Series(common,index=returns.index)
    history = returns.iloc[:lookback]
    mu,cov = estimate(history,ridge)
    mu.to_csv(out/'02_expected_returns.csv')
    history.cov().to_csv(out/'02_sample_covariance.csv')
    cov.to_csv(out/'02_regularized_covariance.csv')
    minw = solve(mu,cov,'min_variance')
    maxw = solve(mu,cov,'max_sharpe',rf=float(rf.loc[history.index].mean()))
    equal = pd.Series(1/len(mu),index=mu.index)
    pd.DataFrame({'MinVariance':minw,'MaxSharpe':maxw,'EqualWeight':equal}).to_csv(out/'03_weights.csv')
    fr, fw = frontier(mu,cov)
    fr.to_csv(out/'04_frontier.csv',index=False)
    fw.to_csv(out/'04_frontier_weights.csv',index=False)
    rows = pd.DataFrame([dict(strategy=name,**portfolio_stats(w,mu,cov,.002))
                        for name,w in [('MinVariance',minw),('MaxSharpe',maxw),('EqualWeight',equal)]])
    chart = [('Efficient frontier',list(zip(fr.volatility_monthly,fr.expected_return_monthly)))]
    names = rows["strategy"].astype(str).tolist()
    coordinates = rows[
        ["volatility_monthly", "expected_return_monthly"]
    ].to_numpy(dtype=float).tolist()

    for name, point in zip(names, coordinates):
        chart.append((name, [(point[0], point[1])]))
    (out/'04_frontier.svg').write_text(svg_plot(chart,'Đường biên hiệu quả · dữ liệu giả lập','Độ lệch chuẩn tháng (%)','Lợi suất kỳ vọng tháng (%)',kind='frontier',x_percent=True,y_percent=True),encoding='utf-8')
    rows.to_csv(out/'05_in_sample_comparison.csv',index=False)
    sharpe_table = export_sharpe_comparison(out, history, rf, maxw)
    print("\nSO SANH SHARPE TRONG MAU - CUNG KY, CUNG RF, CHUA PHI")
    print(sharpe_table.to_string(index=False))
    strategies = {'MinVariance':optimizer_factory('min_variance',rf,ridge),
                  'MaxSharpe':optimizer_factory('max_sharpe',rf,ridge),
                  'EqualWeight':lambda h:pd.Series(1/h.shape[1],index=h.columns)}
    results, tables, crossings = {}, [], {}
    for name, opt in strategies.items():
        runs = run_cost_scenarios(returns,opt,lookback=lookback,rebalance_every=1,decision_lag_periods=1)
        table = comparison_table(runs,rf,benchmark)
        crossings[name] = fee_crossings(table)
        table['strategy'] = name
        tables.append(table); results[name] = runs
        for rate,result in runs.items():
            prefix = f'06_{name}_fee_{rate:.4f}'
            result.periods.to_csv(out/f'{prefix}_periods.csv')
            result.trades.to_csv(out/f'{prefix}_trades.csv',index=False)
            result.weights.to_csv(out/f'{prefix}_weights.csv',index=False)
    combined = pd.concat(tables,ignore_index=True)
    combined.to_csv(out/'06_comparison.csv',index=False)
    cfg = {'synthetic':True,'benchmark_name':'SYNTHETIC_NOT_VN30',
           'universe_selection':'Four simulated assets; fixed universe; not historical VN100',
           'execution_assumption':'Monthly returns; 24-month window; one-month lag; long-only; fractional holdings',
           'rates':[0,.0015,.0025,.0035],'lookback':lookback,'ridge':ridge,
           'rf_estimator':'Mean RF in training window','mean_estimator':'Arithmetic historical mean',
           'covariance_estimator':'Sample covariance ddof=1 plus ridge * identity',
           'fee_crossings':crossings,'versions':{'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__}}
    (out/'run_metadata.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    export_report(out,results,combined,benchmark,cfg)
    print('Stages 1-6 completed on SYNTHETIC data only.')
    print(rows.to_string(index=False))
    print(combined.to_string(index=False))
    print(f'Report: {out.resolve() / "report.html"}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='six_steps_output')
    args = parser.parse_args()
    run(args.output)
