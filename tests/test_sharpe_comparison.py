import unittest

import numpy as np
import pandas as pd

from src.portfolio.sharpe_comparison import compare_sharpes


class AssetSharpeComparisonTests(unittest.TestCase):
    def inputs(self):
        dates = pd.date_range("2020-01-31", periods=4, freq="ME")
        history = pd.DataFrame(
            {"A": [0.01, 0.04, -0.02, 0.03], "B": [0.03, -0.01, 0.02, 0.01]},
            index=dates,
        )
        risk_free = pd.Series([0.001, 0.003, 0.002, 0.004], index=dates)
        weights = pd.Series({"A": 0.7, "B": 0.3})
        return history, risk_free, weights

    def test_manual_formula_same_rf_dates_and_unweighted_mean(self):
        history, risk_free, weights = self.inputs()
        table, _ = compare_sharpes(history, risk_free, weights)

        def sharpe(returns):
            excess = returns - risk_free
            return np.sqrt(12) * excess.mean() / excess.std(ddof=1)

        scores = table.set_index("name").sharpe_annualized
        self.assertAlmostEqual(scores.MaxSharpe, sharpe(history @ weights))
        self.assertAlmostEqual(scores.A, sharpe(history.A))
        self.assertAlmostEqual(scores.B, sharpe(history.B))
        self.assertAlmostEqual(scores.MeanAssetSharpe, (sharpe(history.A) + sharpe(history.B)) / 2)

    def test_missing_rf_rejected(self):
        history, risk_free, weights = self.inputs()
        with self.assertRaises(ValueError):
            compare_sharpes(history, risk_free.iloc[:-1], weights)

    def test_nan_asset_not_silently_removed(self):
        history, risk_free, weights = self.inputs()
        history.iloc[1, 0] = np.nan
        with self.assertRaises(ValueError):
            compare_sharpes(history, risk_free, weights)

    def test_undefined_sharpe_does_not_bias_mean(self):
        history, risk_free, weights = self.inputs()
        history.A = risk_free + 0.01
        table, metadata = compare_sharpes(history, risk_free, weights)
        self.assertTrue(np.isnan(table.iloc[-1].sharpe_annualized))
        self.assertEqual(metadata["valid_asset_sharpes"], 1)
        self.assertIsNone(metadata["max_sharpe_minus_mean_asset"])


if __name__ == "__main__":
    unittest.main()
