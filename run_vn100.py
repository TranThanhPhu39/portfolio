"""Run group period data with explicit methodological choices; no backup data."""
import argparse,json,platform,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from src.portfolio.vn_data import load_periods
from src.portfolio.markowitz import estimate,solve,frontier,optimizer_factory
from src.portfolio.sharpe_comparison import export_sharpe_comparison
from src.backtest.dynamic import make_dynamic_schedule,simulate_dynamic
from src.backtest.performance import comparison_table,fee_crossings
from src.backtest.reporting import export_report
from src.backtest.charts import svg_plot

def run(args):
    out=Path(args.output)
    if out.exists():raise FileExistsError('Choose a new output folder')
    out.mkdir(parents=True)
    cfg={'synthetic':False,'universe_mode':'dynamic','research_status':'EXPLORATORY — unresolved source inconsistencies',
         'rates':[0.,.0015,.0025,.0035],'lookback':24,'lag':1,'ridge':args.ridge,
         'return_basis':args.return_basis,'rf_basis':args.rf_basis,'end':args.end,
         'benchmark_name':'VN30 (group supplied monthly %)',
         'universe_selection':'Group period membership; only members with 24 complete historical return months. Not all 100 names are investable each month. Membership announcement dates not independently verified.',
         'execution_assumption':'24-month training through t-2; trade before month t. Exit constituents sold at boundary; fractional holdings; membership assumed known before trading.',
         'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__},
         'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(args.input).glob('*.csv')}}
    (out/'run_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        r,m,rf,b,prices=load_periods(args.input,args.return_basis,args.rf_basis,args.end)
        r.to_csv(out/'01_returns.csv');m.to_csv(out/'01_membership.csv');rf.to_csv(out/'01_rf.csv',header=['rf_return']);b.to_csv(out/'01_benchmark.csv',header=['return'])
        outputs={};tables=[];crossings={};first_weights={};first_history=None
        for name,kind in [('MinVariance','min_variance'),('MaxSharpe','max_sharpe'),('EqualWeight','equal_weight')]:
            opt=(lambda h:pd.Series(1/h.shape[1],index=h.columns)) if kind=='equal_weight' else optimizer_factory(kind,rf,args.ridge)
            schedule,elig=make_dynamic_schedule(r,m,opt)
            elig.to_csv(out/'eligibility.csv',index=False)
            first=schedule[0];names=elig.loc[(elig.date==r.index[first['position']])&elig.eligible,'ticker'].tolist()
            first_history=r.loc[first['train_start']:first['train_end'],names]
            first_weights[name]=pd.Series(first['weights'],index=r.columns).loc[names]
            runs={rate:simulate_dynamic(r,schedule,rate) for rate in cfg['rates']}
            for rate,result in runs.items():
                prefix=f'{name}_fee_{rate:.4f}'
                result.periods.to_csv(out/f'{prefix}_periods.csv');result.trades.to_csv(out/f'{prefix}_trades.csv',index=False);result.weights.to_csv(out/f'{prefix}_weights.csv',index=False)
                if not np.allclose(result.periods.start_value-result.periods.fee,result.periods.end_value/(1+result.periods.market_return),atol=1e-9):raise AssertionError('Accounting identity')
            t=comparison_table(runs,rf,b);t['strategy']=name;tables.append(t);outputs[name]=runs;crossings[name]=fee_crossings(t)
            print(name,'completed',len(schedule),'months',flush=True)
        mu,cov=estimate(first_history,args.ridge)
        mu.to_csv(out/'02_expected_returns.csv');first_history.cov().to_csv(out/'02_sample_covariance.csv');cov.to_csv(out/'02_regularized_covariance.csv')
        pd.DataFrame(first_weights).to_csv(out/'03_weights.csv')
        fr,fw=frontier(mu,cov);fr.to_csv(out/'04_frontier.csv',index=False);fw.to_csv(out/'04_frontier_weights.csv',index=False)
        chart=[('Efficient frontier',list(zip(fr.volatility_monthly,fr.expected_return_monthly)))]
        for name,w in first_weights.items():chart.append((name,[(float(np.sqrt(w@cov@w)),float(w@mu))]))
        (out/'04_frontier.svg').write_text(svg_plot(chart,'First training window','Monthly volatility','Expected monthly return',kind='frontier',x_percent=True,y_percent=True),encoding='utf-8')
        export_sharpe_comparison(out,first_history,rf,first_weights['MaxSharpe'])
        combined=pd.concat(tables,ignore_index=True);combined.to_csv(out/'comparison.csv',index=False)
        (out/'fee_crossings.json').write_text(json.dumps(crossings,indent=2))
        export_report(out,outputs,combined,b,cfg)
        status={'execution':'PASS','research_acceptance':'NOT_CONFIRMED','months':len(next(iter(outputs.values()))[0.].periods),'eligible_count_min':int(elig.groupby('date').eligible.sum().min()),'eligible_count_max':int(elig.groupby('date').eligible.sum().max()),'source_folder_only':True}
        (out/'RUN_STATUS.json').write_text(json.dumps(status,indent=2));print(json.dumps(status))
    except Exception as exc:
        (out/'RUN_STATUS.json').write_text(json.dumps({'execution':'FAILED','error':str(exc)},indent=2));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',default=str(Path(__file__).parent/'data/vn100_periods'))
    p.add_argument('--output',required=True);p.add_argument('--return-basis',choices=['provided','prices'],required=True)
    p.add_argument('--rf-basis',choices=['annual_effective_percent','monthly_percent'],required=True)
    p.add_argument('--end',default='2026-08');p.add_argument('--ridge',type=float,default=1e-8)
    run(p.parse_args())
