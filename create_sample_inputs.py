"""Create reproducible CSV fixtures; not market data."""
from pathlib import Path
import numpy as np
import pandas as pd


def create(destination):
    out = Path(destination)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260928)
    dates = pd.date_range('2017-01-31', periods=84, freq='ME')
    common = rng.normal(.005, .035, len(dates))
    panel = pd.DataFrame(common[:, None] + rng.normal(.002, .025, (84, 4)),
        index=dates, columns=['SIM_A', 'SIM_B', 'SIM_C', 'SIM_D'])
    panel.rename_axis('date').reset_index().melt(id_vars='date', var_name='ticker', value_name='return').to_csv(out/'returns.csv', index=False)
    pd.DataFrame({'date': dates, 'return': common}).to_csv(out/'benchmark.csv', index=False)
    pd.DataFrame({'date': dates, 'rf_return': .002}).to_csv(out/'risk_free.csv', index=False)


if __name__ == '__main__':
    create(Path(__file__).parent/'sample_inputs')
