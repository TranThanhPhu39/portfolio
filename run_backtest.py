"""CLI: python run_backtest.py --config config/example.json"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import platform
import re
import numpy as np
import pandas as pd
from src.backtest.walk_forward import run_cost_scenarios, validate_returns
from src.backtest.dynamic import (
    validate_dynamic_returns,
    validate_membership,
    make_dynamic_schedule,
    simulate_dynamic,
)
from src.backtest.performance import comparison_table, fee_crossings
from src.backtest.reporting import export_report


def read_monthly(path, columns, *, allow_sparse=False):
    df = pd.read_csv(path, dtype={'ticker': str})
    if not set(columns).issubset(df.columns):
        raise ValueError(f'{path}: required columns {columns}')
    df['date'] = pd.to_datetime(df['date'], errors='raise')
    if df['date'].isna().any() or not df['date'].dt.is_month_end.all():
        raise ValueError(f'{path}: dates must be valid month ends')
    keys = ['date', 'ticker'] if 'ticker' in columns else ['date']
    if df.duplicated(keys).any():
        raise ValueError(f'{path}: duplicate observations')
    value = columns[-1]
    df[value] = pd.to_numeric(df[value], errors='raise')
    if not np.isfinite(df[value]).all() or (df[value] <= -1).any():
        raise ValueError(f'{path}: invalid simple returns')
    if 'ticker' in columns:
        if df.ticker.isna().any() or df.ticker.str.strip().eq('').any():
            raise ValueError('Ticker cannot be empty')
        result = df.pivot(index='date', columns='ticker', values=value).sort_index()
        if allow_sparse:
            validate_dynamic_returns(result)
        else:
            validate_returns(result)
        return result
    return df.set_index('date')[value].sort_index()


def read_membership(path):
    """Read explicit long-form date,ticker,member boolean observations."""
    df = pd.read_csv(path, dtype={'ticker': str, 'member': str})
    required = {'date', 'ticker', 'member'}
    if not required.issubset(df.columns):
        raise ValueError(f'{path}: required columns date,ticker,member')
    df['date'] = pd.to_datetime(df['date'], errors='raise')
    if df['date'].isna().any() or not df['date'].dt.is_month_end.all():
        raise ValueError(f'{path}: dates must be valid month ends')
    if df.duplicated(['date', 'ticker']).any():
        raise ValueError(f'{path}: duplicate membership observations')
    if df.ticker.isna().any() or df.ticker.str.strip().eq('').any():
        raise ValueError('Membership ticker cannot be empty')
    normalized = df['member'].str.strip().str.lower()
    mapping = {'true': True, 'false': False, '1': True, '0': False}
    if not normalized.isin(mapping).all():
        raise ValueError('Membership values must be true/false or 1/0')
    df['member'] = normalized.map(mapping).astype(bool)
    return df.pivot(index='date', columns='ticker', values='member').sort_index()


def execute(config_path):
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    universe_mode = cfg.get('universe_mode')
    if universe_mode not in ('fixed', 'dynamic'):
        raise ValueError('universe_mode must be fixed or dynamic')
    if not isinstance(cfg.get('synthetic'), bool):
        raise ValueError('Set synthetic explicitly to true or false')
    for key in ('data_source', 'benchmark_name', 'return_basis', 'universe_selection', 'execution_assumption'):
        if not isinstance(cfg.get(key), str) or not cfg[key].strip():
            raise ValueError(f'Missing methodology field: {key}')
        if 'REPLACE_WITH' in cfg[key] or 'CONFIRM_' in cfg[key]:
            raise ValueError(f'Complete the research template field: {key}')
    if universe_mode == 'dynamic':
        for key in ('rf_basis', 'end'):
            if not isinstance(cfg.get(key), str) or not cfg[key].strip():
                raise ValueError(f'Missing dynamic methodology field: {key}')
    rates = cfg['rates']
    if not {0., .0015, .0025, .0035}.issubset(rates):
        raise ValueError('Include baseline and all three assigned fee scenarios')
    path_keys = ['returns', 'benchmark', 'risk_free']
    if universe_mode == 'dynamic':
        path_keys.append('membership')
    paths = {key: (config_path.parent / cfg[key]).resolve() for key in path_keys}
    returns = read_monthly(
        paths['returns'], ['date', 'ticker', 'return'],
        allow_sparse=universe_mode == 'dynamic')
    benchmark = read_monthly(paths['benchmark'], ['date', 'return'])
    rf = read_monthly(paths['risk_free'], ['date', 'rf_return'])
    membership = None
    if universe_mode == 'dynamic':
        membership = read_membership(paths['membership'])
        validate_membership(membership, returns)
    if not cfg.get('strategies'):
        raise ValueError('At least one optimizer required')
    outputs, tables, crossings, eligibility = {}, [], {}, {}
    for name, reference in cfg['strategies'].items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError('Strategy names may contain letters, numbers, underscore and hyphen')
        module, attr = reference.split(':')
        if module == 'builtin':
            from src.portfolio.markowitz import optimizer_factory
            if attr == 'equal_weight':
                optimizer = lambda h: pd.Series(1/h.shape[1],index=h.columns)
            elif attr in ('min_variance','max_sharpe'):
                optimizer = optimizer_factory(attr,rf,ridge=cfg['ridge'])
            else:
                raise ValueError('Unknown built-in optimizer')
        else:
            optimizer = getattr(importlib.import_module(module), attr)
        if universe_mode == 'fixed':
            results = run_cost_scenarios(
                returns, optimizer, lookback=cfg['lookback'],
                rebalance_every=cfg['rebalance_every'],
                decision_lag_periods=cfg['decision_lag_periods'], rates=rates)
        else:
            schedule, audit = make_dynamic_schedule(
                returns, membership, optimizer, lookback=cfg['lookback'],
                lag=cfg['decision_lag_periods'],
                rebalance_every=cfg['rebalance_every'])
            results = {rate: simulate_dynamic(returns, schedule, rate) for rate in rates}
            eligibility[name] = audit
        table = comparison_table(results, rf, benchmark)
        crossings[name] = fee_crossings(table)
        table['strategy'] = name
        tables.append(table)
        outputs[name] = results
    # Do not create a report directory until all strategies validate and finish.
    out = (config_path.parent / cfg['output_dir']).resolve()
    out.mkdir(parents=True, exist_ok=False)
    table = pd.concat(tables, ignore_index=True)
    table.to_csv(out / 'comparison.csv', index=False)
    if universe_mode == 'fixed' and 'MaxSharpe' in outputs:
        from src.portfolio.sharpe_comparison import export_sharpe_comparison
        trades = outputs['MaxSharpe'][0.].trades
        first = trades[trades.date == trades.date.min()]
        weights = first.set_index('asset').target_weight
        window = returns.loc[first.train_start.iloc[0]:first.train_end.iloc[0]]
        export_sharpe_comparison(out, window, rf, weights)
    for name, results in outputs.items():
        if name in eligibility:
            eligibility[name].to_csv(out / f'{name}_eligibility.csv', index=False)
        for rate, result in results.items():
            prefix = f'{name}_fee_{rate:.6f}'
            result.periods.to_csv(out / f'{prefix}_periods.csv')
            result.trades.to_csv(out / f'{prefix}_trades.csv', index=False)
            result.weights.to_csv(out / f'{prefix}_weights.csv', index=False)
    metadata = {'config': cfg, 'fee_crossings': crossings,
        'input_sha256': {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()},
        'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__}}
    (out / 'run_metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    export_report(out, outputs, table, benchmark, cfg)
    print(table.to_string(index=False))
    print(f'Report: {out / "report.html"}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    execute(parser.parse_args().config)
