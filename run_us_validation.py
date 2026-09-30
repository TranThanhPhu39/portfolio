"""30 real US stock prices, 2018-2022: reproducible integration test, NOT VN research."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
import urllib.request
import zipfile
import numpy as np
import pandas as pd
from run_backtest import execute
from src.portfolio.prices import prices_to_returns
from src.portfolio.markowitz import estimate, solve, frontier, portfolio_stats
from src.backtest.charts import svg_plot
from src.backtest.reporting import export_report
from src.backtest.walk_forward import BacktestResult

TICKERS = 'AAPL MSFT JNJ XOM GE KO PFE WMT CAT IBM DIS MCD CVX HD MMM BA AXP NKE PG TRV UNH VZ V JPM CSCO INTC MRK GS HON CRM'.split()
FF_URL = 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip'


def fetch(url, path):
    if path.exists():
        return path.read_bytes()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'}),timeout=45) as response:
                content = response.read()
            path.write_bytes(content)
            return content
        except Exception:
            if attempt == 2: raise
            time.sleep(2)


def stock(symbol, raw):
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1=1514764800&period2=1672531200&interval=1d'
    path=raw/f'{symbol}.json'
    payload=fetch(url,path)
    doc=json.loads(payload)['chart']
    if doc.get('error'): raise ValueError(f'{symbol}: {doc["error"]}')
    r=doc['result'][0]
    if r['meta']['currency'] != 'USD': raise ValueError('Expected USD')
    dates=pd.to_datetime(r['timestamp'],unit='s',utc=True).tz_convert('America/New_York').tz_localize(None).normalize()
    series=pd.Series(r['indicators']['adjclose'][0]['adjclose'],index=dates,name=symbol)
    if series.index.has_duplicates: raise ValueError(f'{symbol}: duplicate dates')
    series=series.loc['2018-01-01':'2022-12-31'].sort_index()
    print(f'Downloaded/cached {symbol}: {len(series)} dates',flush=True)
    return series,{'symbol':symbol,'url':url,'sha256':hashlib.sha256(payload).hexdigest()}


def parse_rf(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text=z.read(z.namelist()[0]).decode('utf-8-sig')
    rows=[]
    for line in text.splitlines():
        cells=line.strip().split(',')
        if re.fullmatch(r'\d{6}',cells[0].strip()) and len(cells)>=5:
            value=float(cells[4])
            if value in (-99.99,-999.): raise ValueError('Missing RF sentinel')
            rows.append((pd.Period(cells[0].strip(),freq='M').to_timestamp('M'),value/100))
    if not rows: raise ValueError('No monthly RF rows parsed')
    dates,values=zip(*rows)
    return pd.Series(values,index=pd.DatetimeIndex(dates),name='rf_return')


def prepare(folder):
    raw=folder/'raw'; raw.mkdir(parents=True,exist_ok=True)
    data=folder/'data'; data.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        downloaded=list(pool.map(lambda symbol:stock(symbol,raw),TICKERS+['SPY']))
    daily=pd.concat([item[0] for item in downloaded],axis=1).sort_index()
    # Require every requested stock on every observed SPY trading date; never drop failed tickers.
    missing=daily.isna().sum()
    daily.to_csv(data/'us_test_prices_including_spy.csv',index_label='date')
    audit={'stocks':len(TICKERS),'daily_rows':len(daily),'missing_by_symbol':missing.to_dict(),
           'start':str(daily.index.min().date()),'end':str(daily.index.max().date()),
           'zero_or_negative_prices':int((daily<=0).sum().sum()),
           'calendar_check':'Common observed dates including SPY, not independent exchange calendar validation',
           'monthly_aggregation':'Last observed trading-day adjusted price in each calendar month; no filling'}
    (data/'quality.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    if missing.any() or not np.isfinite(daily.to_numpy()).all() or (daily<=0).any().any():
        raise ValueError('Daily price quality failed; inspect quality.json; no imputation performed')
    monthly=daily.resample('ME').last()
    if len(monthly)!=60: raise ValueError('Expected all 60 price months from 2018 through 2022')
    monthly[TICKERS].rename_axis('date').reset_index().melt(id_vars='date',var_name='ticker',value_name='adjusted_price').to_csv(data/'monthly_prices.csv',index=False)
    daily[TICKERS].to_csv(data/'us_test_prices.csv',index_label='date')
    returns=prices_to_returns(monthly[TICKERS])
    returns.rename_axis('date').reset_index().melt(id_vars='date',var_name='ticker',value_name='return').to_csv(data/'returns.csv',index=False)
    b=prices_to_returns(monthly[['SPY']]).SPY.rename('return')
    b.to_csv(data/'benchmark.csv',index_label='date')
    rf_payload=fetch(FF_URL,raw/'F-F_Research_Data_Factors_CSV.zip')
    rf=parse_rf(rf_payload).reindex(returns.index)
    if rf.isna().any(): raise ValueError('Missing RF months')
    rf.to_csv(data/'risk_free.csv',index_label='date')
    source={'retrieved_or_cache_checked_utc':datetime.now(timezone.utc).isoformat(),
            'prices': [item[1] for item in downloaded],
            'rf':{'url':FF_URL,'sha256':hashlib.sha256(rf_payload).hexdigest()},
            'universe':'Original 30 tickers from user get_test_data.py; selected retrospectively; survivorship/selection bias not removed',
            'price_basis':'Yahoo adjusted close; provider historical revisions possible; corporate actions not independently audited',
            'scope':'US real-data software validation only, not VN30/VN100 research'}
    (data/'sources.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
    cfg={'synthetic':False,'universe_mode':'fixed','data_source':'Yahoo Finance adjusted close + Kenneth French monthly RF; see data/sources.json',
         'benchmark_name':'SPY adjusted return (US test, not VN30)',
         'return_basis':'Simple monthly returns from Yahoo adjusted closing prices for stocks and SPY',
         'universe_selection':'30 US stocks chosen retrospectively for software validation; NOT a historical unbiased investment universe',
         'execution_assumption':'24-month historical mean/covariance, ridge=1e-8; monthly rebalance; one-month implementation lag; fractional holdings; no terminal liquidation',
         'returns':'data/returns.csv','benchmark':'data/benchmark.csv','risk_free':'data/risk_free.csv',
         'output_dir':'results','lookback':24,'rebalance_every':1,'decision_lag_periods':1,
         'ridge':1e-8,'rates':[0,.0015,.0025,.0035],
         'strategies':{'MinVariance':'builtin:min_variance','MaxSharpe':'builtin:max_sharpe','EqualWeight':'builtin:equal_weight'}}
    (folder/'config.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    return returns,rf,b,cfg


def run(folder):
    folder=Path(folder).resolve(); folder.mkdir(parents=True,exist_ok=True)
    if (folder/'results').exists(): raise FileExistsError('Results exist; choose another folder or reuse saved data via run_backtest.py and a new output_dir')
    returns,rf,benchmark,cfg=prepare(folder)
    out=execute(folder/'config.json')
    history=returns.iloc[:cfg['lookback']]
    mu,cov=estimate(history,cfg['ridge']); risk=float(rf.reindex(history.index).mean())
    mu.to_csv(out/'02_expected_returns.csv'); history.cov().to_csv(out/'02_sample_covariance.csv'); cov.to_csv(out/'02_regularized_covariance.csv')
    weights={name:solve(mu,cov,kind,rf=risk) for name,kind in [('MinVariance','min_variance'),('MaxSharpe','max_sharpe')]}
    weights['EqualWeight']=pd.Series(1/len(mu),index=mu.index)
    pd.DataFrame(weights).to_csv(out/'03_weights.csv')
    fr,fw=frontier(mu,cov)
    fr.to_csv(out/'04_frontier.csv',index=False);fw.to_csv(out/'04_frontier_weights.csv',index=False)
    rows=pd.DataFrame([dict(strategy=n,**portfolio_stats(w,mu,cov,risk)) for n,w in weights.items()])
    rows.to_csv(out/'05_in_sample_comparison.csv',index=False)
    chart=([('Efficient frontier',list(zip(fr.volatility_monthly,fr.expected_return_monthly)))]+
        [(str(r.strategy),[(float(r.volatility_monthly),float(r.expected_return_monthly))]) for r in rows.itertuples()])
    (out/'04_frontier.svg').write_text(svg_plot(chart,'US 30 stocks · First training window','Monthly volatility (%)','Expected monthly return (%)',kind='frontier',x_percent=True,y_percent=True),encoding='utf-8')
    outputs={}
    for name in weights:
        outputs[name]={}
        for rate in cfg['rates']:
            prefix=f'{name}_fee_{rate:.6f}'
            periods=pd.read_csv(out/f'{prefix}_periods.csv',index_col='date',parse_dates=True)
            outputs[name][rate]=BacktestResult(periods,pd.read_csv(out/f'{prefix}_trades.csv'),pd.read_csv(out/f'{prefix}_weights.csv'))
    table=pd.read_csv(out/'comparison.csv')
    export_report(out,outputs,table,benchmark,cfg)
    print('SUCCESS: all six stages on 30 real US stocks. Not Vietnam research.',flush=True)
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='us30_validation')
    run(p.parse_args().output)
