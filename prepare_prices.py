"""Convert validated month-end adjusted prices to the runner's long returns CSV."""
import argparse
from pathlib import Path
from src.portfolio.prices import load_prices


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    destination=Path(args.output)
    if destination.exists():
        raise FileExistsError('Output already exists; select a new name')
    prices,returns=load_prices(args.input)
    destination.parent.mkdir(parents=True,exist_ok=True)
    returns.rename_axis('date').reset_index().melt(id_vars='date',var_name='ticker',value_name='return').to_csv(destination,index=False)
    print(f'Validated {len(prices)} price months; exported {len(returns)} return months, {returns.shape[1]} assets.')
