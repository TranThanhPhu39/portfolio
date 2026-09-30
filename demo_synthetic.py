"""Run from package root: python demo_synthetic.py. ALL DATA ARE SYNTHETIC."""
from pathlib import Path
import json
import html
import numpy as np
import pandas as pd
from src.backtest.walk_forward import run_cost_scenarios
from src.backtest.performance import comparison_table, fee_crossings


def equal_weight_demo(history):
    # Integration stub only: NOT Markowitz, not a claim about investment efficacy.
    return pd.Series(1/history.shape[1],index=history.columns)


from src.backtest.charts import svg_plot


def main():
    out=Path('demo_outputs'); out.mkdir(exist_ok=True)
    rng=np.random.default_rng(20260928)
    dates=pd.date_range('2017-01-31',periods=84,freq='ME')
    common=rng.normal(.005,.035,len(dates))
    returns=pd.DataFrame(common[:,None]+rng.normal(.002,.025,(len(dates),4)),
                         index=dates,columns=['SIM_A','SIM_B','SIM_C','SIM_D'])
    benchmark=pd.Series(common,index=dates,name='SYNTHETIC_BENCHMARK_NOT_VN30')
    rf=pd.Series(.002,index=dates,name='synthetic_rf')
    results=run_cost_scenarios(returns,equal_weight_demo,lookback=24,rebalance_every=1,
                               decision_lag_periods=1)
    table=comparison_table(results,rf,benchmark)
    table.to_csv(out/'SYNTHETIC_comparison.csv',index=False)
    curves=[]; drawdowns=[]
    for rate,r in results.items():
        label=f'DEMO equal weight; fee {100*rate:.2f}%'
        prefix=f'SYNTHETIC_fee_{rate:.4f}'
        r.periods.to_csv(out/f'{prefix}_periods.csv')
        r.trades.to_csv(out/f'{prefix}_trades.csv',index=False)
        r.weights.to_csv(out/f'{prefix}_weights.csv',index=False)
        value=np.r_[1.,r.periods.end_value.to_numpy()]
        curves.append((label,list(enumerate(value))))
        dd=value/np.maximum.accumulate(value)-1
        drawdowns.append((label,list(enumerate(dd))))
    b=(1+benchmark.reindex(next(iter(results.values())).periods.index)).cumprod()
    bv=np.r_[1.,b.to_numpy()]
    curves.append(('SYNTHETIC benchmark, not VN30',list(enumerate(bv))))
    drawdowns.append(('SYNTHETIC benchmark, not VN30',list(enumerate(bv/np.maximum.accumulate(bv)-1))))
    sharpes=[(100*rate,float(table.iloc[i].sharpe)) for i,rate in enumerate(results)]
    bench_sharpe=float(table.iloc[-1].sharpe)
    charts={
        'equity.svg':svg_plot(curves,'SYNTHETIC DEMO - Equity','Out-of-sample month','Wealth / initial wealth'),
        'drawdown.svg':svg_plot(drawdowns,'SYNTHETIC DEMO - Drawdown','Out-of-sample month','Drawdown (decimal)'),
        'sharpe_vs_fee.svg':svg_plot([('DEMO equal weight',sharpes),('Synthetic benchmark',[(0,bench_sharpe),(.35,bench_sharpe)])],
                            'SYNTHETIC DEMO - Sharpe vs fee','Fee per buy/sell notional (%)','Annualized Sharpe')}
    for name,svg in charts.items(): (out/name).write_text(svg,encoding='utf-8')
    crossing=fee_crossings(table)
    config={'synthetic':True,'strategy':'equal_weight_stub_NOT_Markowitz','seed':20260928,
            'lookback_months':24,'rebalance_months':1,'implementation_lag_months':1,
            'rates':list(results),'threshold_result':crossing}
    (out/'run_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    body='<h1>Backtest demo - DU LIEU GIA LAP</h1><p>Khong phai VN30, khong phai ket qua nghien cuu. Chien luoc chia deu chi de kiem tra ket noi.</p>'
    body+=table.to_html(index=False,float_format=lambda x:f'{x:.6f}')
    body+=''.join(charts.values())
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Synthetic backtest demo</title><style>body{font-family:Arial;max-width:1000px;margin:32px auto;color:#1e293b}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ddd}svg{max-width:760px;display:block;margin:24px 0}</style>'+body,encoding='utf-8')
    print(table.to_string(index=False)); print(crossing)
    print('Outputs: demo_outputs/report.html (SYNTHETIC ONLY)')


if __name__=='__main__': main()
