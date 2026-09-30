"""Monthly changing eligibility; missing returns are allowed only for unheld assets."""
import numpy as np
import pandas as pd
from .transaction_costs import rebalance, validate_weights
from .walk_forward import BacktestResult

def make_dynamic_schedule(returns, membership, optimizer, lookback=24, lag=1):
    if lookback<2 or lag<1: raise ValueError('Require lookback>=2 and lag>=1')
    if not returns.index.equals(membership.index) or not returns.columns.equals(membership.columns):
        raise ValueError('Membership must align exactly with return panel')
    if returns.index.has_duplicates or not returns.index.is_monotonic_increasing or returns.columns.has_duplicates:
        raise ValueError('Duplicate/unsorted dates or assets')
    if not np.all(np.diff(returns.index.to_period('M').asi8)==1): raise ValueError('Missing calendar month')
    finite=returns.notna()
    if np.isinf(returns.to_numpy()).any() or (returns[finite]<=-1).any().any(): raise ValueError('Invalid returns')
    schedule=[]; audit=[]
    for pos in range(lookback+lag,len(returns)):
        hist=returns.iloc[pos-lag-lookback:pos-lag]
        members=membership.iloc[pos].astype(bool)
        eligible=members & hist.notna().all()
        names=returns.columns[eligible]
        if len(names)<2: raise ValueError(f'Insufficient eligible assets at {returns.index[pos]}')
        sub=hist.loc[:,names].copy()
        w=validate_weights(optimizer(sub),names)
        target=pd.Series(0.,index=returns.columns);target.loc[names]=w
        schedule.append(dict(position=pos,train_start=sub.index[0],train_end=sub.index[-1],weights=target.to_numpy()))
        for name in returns.columns[members]:
            audit.append(dict(date=returns.index[pos],ticker=name,eligible=bool(eligible[name]),training_months=int(hist[name].notna().sum())))
    if not schedule:raise ValueError('Not enough data for training and evaluation')
    return schedule,pd.DataFrame(audit)

def simulate_dynamic(returns,schedule,rate):
    if not 0<=rate<1:raise ValueError('Invalid fee rate')
    orders={s['position']:s for s in schedule}
    if len(orders)!=len(schedule):raise ValueError('Duplicate orders')
    h=np.zeros(returns.shape[1]);cash=1.;periods=[];trades=[];weights=[]
    for pos in range(min(orders),len(returns)):
        date=returns.index[pos];before=float(h.sum()+cash);old=h.copy();fee=turn=0.
        if pos in orders:
            s=orders[pos]
            if s['train_end']>=date:raise ValueError('Look-ahead in schedule')
            target=pd.Series(s['weights'],index=returns.columns)
            w=validate_weights(target,returns.columns)
            h,delta,fee,turn=rebalance(h,cash,w,rate);cash=0.
            for k,name in enumerate(returns.columns):
                trades.append(dict(date=date,asset=name,train_start=s['train_start'],train_end=s['train_end'],pretrade_weight=old[k]/before,target_weight=w[k],trade_value=delta[k],fee=abs(delta[k])*rate))
        after=float(h.sum());r=returns.iloc[pos].to_numpy(float);held=h>0
        if not np.isfinite(r[held]).all() or (r[held]<=-1).any():raise ValueError(f'Missing/invalid return for held asset at {date}')
        for k,name in enumerate(returns.columns):weights.append(dict(date=date,asset=name,start_weight=h[k]/after))
        h[held]*=1+r[held]  # Never replace an unknown held-asset return by zero.
        end=float(h.sum())
        periods.append(dict(date=date,start_value=before,fee=fee,turnover_two_way=turn,rebalanced=pos in orders,market_return=end/after-1,net_return=end/before-1,end_value=end))
    return BacktestResult(pd.DataFrame(periods).set_index('date'),pd.DataFrame(trades),pd.DataFrame(weights))
