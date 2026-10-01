import unittest

import numpy as np
import pandas as pd

from src.backtest.benchmark import daily_to_monthly
from src.backtest.performance import comparison_table, fee_crossings, metrics
from src.backtest.transaction_costs import rebalance
from src.backtest.walk_forward import make_schedule, run_cost_scenarios, simulate


def panel(months=12):
    return pd.DataFrame(
        {"A": np.full(months, 0.02), "B": np.full(months, 0.01)},
        index=pd.date_range("2020-01-31", periods=months, freq="ME"),
    )


def equal_weights(history):
    return pd.Series(1 / history.shape[1], index=history.columns)


class BacktestTests(unittest.TestCase):
    def test_initial_fee_self_financing(self):
        holdings, trades, fee, _ = rebalance([0, 0], 100, [0.5, 0.5], 0.01)
        self.assertAlmostEqual(holdings.sum(), 100 / 1.01)
        self.assertAlmostEqual(holdings.sum() + fee, 100)
        self.assertAlmostEqual(fee, 0.01 * abs(trades).sum())

    def test_switch_buy_and_sell_fee(self):
        holdings, _, fee, _ = rebalance([100, 0], 0, [0, 1], 0.01)
        self.assertAlmostEqual(holdings.sum(), 100 * 0.99 / 1.01)
        self.assertAlmostEqual(fee, 0.01 * (100 + holdings.sum()))

    def test_no_trade_no_fee(self):
        _, _, fee, _ = rebalance([60, 40], 0, [0.6, 0.4], 0.0035)
        self.assertAlmostEqual(fee, 0, places=10)

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            rebalance([10, 10], 0, [-0.1, 1.1], 0.01)
        with self.assertRaises(ValueError):
            rebalance([10], 0, [1], np.nan)

    def test_training_window_and_lag(self):
        data = panel()
        seen = []

        def optimizer(history):
            seen.append(history.index.copy())
            return equal_weights(history)

        schedule = make_schedule(data, optimizer, 3, 2, 1)
        self.assertEqual(schedule[0]["position"], 4)
        self.assertEqual(seen[0][-1], data.index[2])

    def test_future_changes_do_not_change_past_weights(self):
        data = panel()

        def optimizer(history):
            return history.mean() / history.mean().sum()

        first = make_schedule(data, optimizer, 3, 1, 1)[0]["weights"]
        data.iloc[4:] = 0.8
        np.testing.assert_array_equal(
            first, make_schedule(data, optimizer, 3, 1, 1)[0]["weights"]
        )

    def test_buy_hold_drift_and_turnover(self):
        data = panel(5)
        data.iloc[:] = 0
        data.iloc[2] = [0.2, 0]
        result = simulate(data, make_schedule(data, equal_weights, 2, 1, 0), 0, 100)
        self.assertAlmostEqual(result.periods.iloc[0].end_value, 110)
        self.assertAlmostEqual(result.periods.iloc[1].turnover_two_way, 10 / 110)

    def test_fee_scenarios_share_dates(self):
        results = run_cost_scenarios(panel(), equal_weights, lookback=3, rebalance_every=2)
        for result in results.values():
            self.assertTrue(result.periods.index.equals(results[0.0].periods.index))
        self.assertGreater(
            results[0.0].periods.end_value.iloc[-1],
            results[0.0035].periods.end_value.iloc[-1],
        )

    def test_invalid_inputs_rejected(self):
        missing = panel()
        missing.iloc[3, 0] = np.nan
        with self.assertRaises(ValueError):
            make_schedule(missing, equal_weights, 3, 1)
        data = panel()
        with self.assertRaises(ValueError):
            make_schedule(data.drop(data.index[3]), equal_weights, 3, 1)
        with self.assertRaises(ValueError):
            make_schedule(
                data, lambda history: pd.Series([0.5, 0.5], index=["X", "Y"]), 3, 1
            )

    def test_drawdown_and_sharpe(self):
        returns = pd.Series([-0.1, 0], index=panel(2).index)
        result = metrics(returns, returns * 0)
        self.assertAlmostEqual(result["max_drawdown"], -0.1)
        self.assertAlmostEqual(result["cagr"], 0.9**6 - 1)
        variable = pd.Series([0.01, 0.03, 0.02], index=panel(3).index)
        risk_free = pd.Series([0.001, 0.002, 0.003], index=variable.index)
        expected = np.sqrt(12) * (variable - risk_free).mean() / (
            variable - risk_free
        ).std(ddof=1)
        self.assertAlmostEqual(metrics(variable, risk_free)["sharpe"], expected)

    def test_benchmark_missing_date_rejected(self):
        data = panel()
        results = run_cost_scenarios(data, equal_weights, lookback=3, rebalance_every=1)
        with self.assertRaises(ValueError):
            comparison_table(results, data.A * 0, data.A.iloc[:-1])

    def test_daily_returns_compounded(self):
        daily = pd.Series(
            [0.1, -0.1], index=pd.to_datetime(["2020-01-02", "2020-01-03"])
        )
        self.assertAlmostEqual(daily_to_monthly(daily).iloc[0], -0.01)

    def test_fee_crossing_is_a_bracket(self):
        table = pd.DataFrame(
            {
                "name": ["strategy", "strategy", "strategy", "benchmark"],
                "transaction_cost_rate": [0, 0.0015, 0.0035, np.nan],
                "sharpe": [0.8, 0.6, 0.4, 0.5],
            }
        )
        self.assertEqual(fee_crossings(table)["brackets"], [(0.0015, 0.0035)])


if __name__ == "__main__":
    unittest.main()
