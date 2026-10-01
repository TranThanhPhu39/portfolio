"""Explicit conversion of group period files. Original files remain unchanged."""
from pathlib import Path
import numpy as np
import pandas as pd

def load_periods(folder,return_basis='provided',rf_basis='annual_effective_percent',end='2026-08'):
    paths=sorted(Path(folder).glob('Top100_Ky*.csv'))
    if not paths:raise ValueError('No period CSV files')
    frames=[]
    for p in paths:
        try:df=pd.read_csv(p,encoding='utf-8-sig')
        except UnicodeDecodeError:df=pd.read_csv(p,encoding='cp1252')
        df['source_file']=p.name;frames.append(df)
    raw=pd.concat(frames,ignore_index=True)
    raw['observed_date']=pd.to_datetime(raw.Date,format='%d/%m/%Y',errors='raise')
    raw['date']=raw.observed_date.dt.to_period('M').dt.to_timestamp('M')
    if raw.duplicated(['date','Ticker']).any():raise ValueError('Duplicate ticker month')
    # A month-end label alone cannot turn partial-month data into a full month.
    partial=raw.loc[raw.observed_date!=raw.date,'date'].unique()
    last=pd.Period(end,freq='M').to_timestamp('M')
    if any(pd.Timestamp(d)<=last for d in partial):raise ValueError('Selected range includes non-month-end observations; choose earlier end')
    data=raw.loc[raw.date<=last].copy()
    def num(s):return pd.to_numeric(s.astype(str).str.replace(',','',regex=False).where(s.notna(),np.nan),errors='raise')
    for c in ['Monthly Return (%)','Close (EOM)','rRF','VN30']:data[c]=num(data[c])
    for c in ['rRF','VN30']:
        if data.groupby('date')[c].nunique(dropna=False).gt(1).any():raise ValueError(f'Conflicting {c} by date')
    data['present']=True
    membership=data.pivot(index='date',columns='Ticker',values='present').eq(True).sort_index()
    prices=data.pivot(index='date',columns='Ticker',values='Close (EOM)').reindex_like(membership)
    if return_basis=='provided':returns=data.pivot(index='date',columns='Ticker',values='Monthly Return (%)').reindex_like(membership)/100
    elif return_basis=='prices':
        returns=prices.pct_change(fill_method=None)
        # First price month has no preceding price; do not count it as a return month.
        if returns.iloc[0].isna().all():
            returns=returns.iloc[1:];membership=membership.loc[returns.index]
    else:raise ValueError('Unknown return basis')
    monthly=data.groupby('date')[['rRF','VN30']].first().reindex(returns.index)
    if rf_basis=='annual_effective_percent':rf=(1+monthly.rRF/100)**(1/12)-1
    elif rf_basis=='monthly_percent':rf=monthly.rRF/100
    else:raise ValueError('Unknown RF basis')
    if not np.isfinite(rf).all():raise ValueError('Missing RF')
    return returns,membership,rf,monthly.VN30/100,prices
