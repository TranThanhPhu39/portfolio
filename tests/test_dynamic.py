import unittest

import numpy as np
import pandas as pd

from src.backtest.dynamic import make_dynamic_schedule, simulate_dynamic


class DynamicTests(unittest.TestCase):
    def setUp(self):
        self.returns = pd.DataFrame(
            0.01,
            index=pd.date_range("2020-01-31", periods=9, freq="ME"),
            columns=["A", "B", "C"],
        )
        self.membership = pd.DataFrame(
            True, index=self.returns.index, columns=self.returns.columns
        )
        self.optimizer = lambda history: pd.Series(
            1 / history.shape[1], index=history.columns
        )

    def test_entry_waits_for_complete_training(self):
        self.returns.loc[self.returns.index[:3], "C"] = np.nan
        schedule, _ = make_dynamic_schedule(
            self.returns, self.membership, self.optimizer, 3, 1
        )
        self.assertEqual(schedule[0]["weights"][2], 0)
        self.assertGreater(schedule[3]["weights"][2], 0)

    def test_exit_liquidation_is_charged(self):
        self.membership.loc[self.returns.index[5] :, "C"] = False
        schedule, _ = make_dynamic_schedule(
            self.returns, self.membership, self.optimizer, 3, 1
        )
        result = simulate_dynamic(self.returns, schedule, 0.0035)
        trade = result.trades.query('asset == "C"').set_index("date").loc[
            self.returns.index[5]
        ]
        self.assertLess(trade.trade_value, 0)
        self.assertGreater(trade.fee, 0)
        self.assertEqual(trade.target_weight, 0)

    def test_missing_held_return_rejected(self):
        schedule, _ = make_dynamic_schedule(
            self.returns, self.membership, self.optimizer, 3, 1
        )
        self.returns.iloc[4, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "held asset"):
            simulate_dynamic(self.returns, schedule, 0)

    def test_missing_unheld_return_allowed(self):
        self.membership["C"] = False
        self.returns["C"] = np.nan
        schedule, _ = make_dynamic_schedule(
            self.returns, self.membership, self.optimizer, 3, 1
        )
        result = simulate_dynamic(self.returns, schedule, 0)
        np.testing.assert_allclose(
            result.periods.end_value.to_numpy(), 1.01 ** np.arange(1, 6)
        )

    def test_missing_membership_rejected(self):
        membership = self.membership.astype(object)
        membership.iloc[-1, 0] = None
        with self.assertRaisesRegex(ValueError, "cannot contain missing"):
            make_dynamic_schedule(self.returns, membership, self.optimizer, 3, 1)

    def test_non_boolean_membership_rejected(self):
        membership = self.membership.astype(str)
        with self.assertRaisesRegex(ValueError, "explicit booleans"):
            make_dynamic_schedule(self.returns, membership, self.optimizer, 3, 1)

    def test_rebalance_interval_is_respected(self):
        schedule, _ = make_dynamic_schedule(
            self.returns, self.membership, self.optimizer, 3, 1,
            rebalance_every=2,
        )
        self.assertEqual([item["position"] for item in schedule], [4, 6, 8])

    def test_membership_change_forces_exit_between_regular_rebalances(self):
        self.membership.loc[self.returns.index[5] :, "C"] = False
        schedule, _ = make_dynamic_schedule(
            self.returns, self.membership, self.optimizer, 3, 1,
            rebalance_every=3,
        )
        self.assertEqual([item["position"] for item in schedule], [4, 5, 7])
        self.assertEqual(schedule[1]["weights"][2], 0)

    def test_invalid_schedule_rejected(self):
        schedule, _ = make_dynamic_schedule(
            self.returns, self.membership, self.optimizer, 3, 1
        )
        schedule[0]["position"] = len(self.returns)
        with self.assertRaisesRegex(ValueError, "execution position"):
            simulate_dynamic(self.returns, schedule, 0)


if __name__ == "__main__":
    unittest.main()
