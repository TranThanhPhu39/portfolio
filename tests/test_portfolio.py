import unittest

import numpy as np
import pandas as pd

from src.portfolio.markowitz import (
    estimate,
    frontier,
    optimizer_factory,
    portfolio_stats,
    solve,
)
from src.portfolio.prices import prices_to_returns


class Stage1Prices(unittest.TestCase):
    def panel(self):
        return pd.DataFrame(
            {"A": [100.0, 110.0, 99.0], "B": [50.0, 50.0, 55.0]},
            index=pd.date_range("2020-01-31", periods=3, freq="ME"),
        )

    def test_hand_calculated_returns(self):
        returns = prices_to_returns(self.panel())
        np.testing.assert_allclose(returns.A, [0.1, -0.1])
        np.testing.assert_allclose(returns.B, [0, 0.1])

    def test_missing_not_filled(self):
        prices = self.panel()
        prices.iloc[1, 0] = np.nan
        with self.assertRaises(ValueError):
            prices_to_returns(prices)

    def test_zero_price_rejected(self):
        prices = self.panel()
        prices.iloc[1, 0] = 0
        with self.assertRaises(ValueError):
            prices_to_returns(prices)

    def test_missing_month_rejected(self):
        prices = self.panel()
        prices.index = pd.to_datetime(["2020-01-31", "2020-03-31", "2020-04-30"])
        with self.assertRaises(ValueError):
            prices_to_returns(prices)


class Stage2Estimation(unittest.TestCase):
    def test_known_mean_and_sample_covariance(self):
        history = pd.DataFrame(
            {"A": [0.01, 0.02, 0.03], "B": [0.02, 0.04, 0.06]},
            index=pd.date_range("2020-01-31", periods=3, freq="ME"),
        )
        mean, covariance = estimate(history, ridge=0)
        np.testing.assert_allclose(mean, [0.02, 0.04])
        np.testing.assert_allclose(covariance, [[0.0001, 0.0002], [0.0002, 0.0004]])

    def test_ridge_is_explicit(self):
        history = pd.DataFrame(
            {"A": [0.01, 0.01, 0.01]},
            index=pd.date_range("2020-01-31", periods=3, freq="ME"),
        )
        _, covariance = estimate(history, ridge=1e-6)
        self.assertAlmostEqual(covariance.iloc[0, 0], 1e-6)


class Stage3Optimization(unittest.TestCase):
    def inputs(self):
        mean = pd.Series([0.02, 0.03], index=["A", "B"])
        covariance = pd.DataFrame(
            [[0.04, 0], [0, 0.09]], index=["A", "B"], columns=["A", "B"]
        )
        return mean, covariance

    def test_min_variance_analytic_solution(self):
        mean, covariance = self.inputs()
        np.testing.assert_allclose(solve(mean, covariance), [9 / 13, 4 / 13], atol=1e-6)

    def test_max_sharpe_analytic_solution(self):
        mean, covariance = self.inputs()
        weights = solve(mean, covariance, "max_sharpe", rf=0.005)
        expected = np.linalg.solve(covariance, mean - 0.005)
        expected /= expected.sum()
        np.testing.assert_allclose(weights, expected, atol=1e-5)

    def test_negative_excess_returns_best_vertex(self):
        mean, covariance = self.inputs()
        np.testing.assert_allclose(
            solve(mean, covariance, "max_sharpe", rf=0.1), [0, 1]
        )

    def test_indefinite_covariance_rejected(self):
        mean, covariance = self.inputs()
        covariance.iloc[:] = [[1, 2], [2, 1]]
        with self.assertRaises(ValueError):
            solve(mean, covariance)

    def test_covariance_labels_reordered(self):
        mean, covariance = self.inputs()
        np.testing.assert_allclose(
            solve(mean, covariance),
            solve(mean, covariance.loc[["B", "A"], ["B", "A"]]),
        )

    def test_training_rf_does_not_use_future(self):
        dates = pd.date_range("2020-01-31", periods=8, freq="ME")
        history = pd.DataFrame(
            np.random.default_rng(1).normal(0.02, 0.01, (8, 2)),
            index=dates,
            columns=["A", "B"],
        )
        risk_free = pd.Series(0.001, index=dates)
        first = optimizer_factory("max_sharpe", risk_free)(history.iloc[:5])
        risk_free.iloc[5:] = 0.9
        np.testing.assert_allclose(
            first, optimizer_factory("max_sharpe", risk_free)(history.iloc[:5])
        )


class Stage4Frontier(unittest.TestCase):
    def test_equal_means_redundant_target(self):
        mean, covariance = Stage3Optimization().inputs()
        mean[:] = 0.02
        points, weights = frontier(mean, covariance, 3)
        np.testing.assert_allclose(points.expected_return_monthly, 0.02)
        np.testing.assert_allclose(weights.iloc[0], [9 / 13, 4 / 13], atol=1e-6)

    def test_feasible_efficient_branch(self):
        mean, covariance = Stage3Optimization().inputs()
        points, weights = frontier(mean, covariance, 8)
        np.testing.assert_allclose(weights.sum(axis=1), 1, atol=1e-8)
        self.assertTrue((weights.to_numpy() >= 0).all())
        self.assertTrue((np.diff(points.expected_return_monthly) >= -1e-8).all())
        self.assertTrue((np.diff(points.volatility_monthly) >= -1e-8).all())

    def test_infeasible_target_rejected(self):
        mean, covariance = Stage3Optimization().inputs()
        with self.assertRaises(ValueError):
            solve(mean, covariance, target=0.9)


class Stage5Comparison(unittest.TestCase):
    def test_optimized_objectives_beat_equal_weight_in_sample(self):
        mean, covariance = Stage3Optimization().inputs()
        equal = pd.Series([0.5, 0.5], index=mean.index)
        baseline = portfolio_stats(equal, mean, covariance, 0.005)
        minimum = portfolio_stats(solve(mean, covariance), mean, covariance, 0.005)
        maximum = portfolio_stats(
            solve(mean, covariance, "max_sharpe", rf=0.005),
            mean,
            covariance,
            0.005,
        )
        self.assertLessEqual(
            minimum["volatility_monthly"], baseline["volatility_monthly"] + 1e-8
        )
        self.assertGreaterEqual(
            maximum["sharpe_annualized"], baseline["sharpe_annualized"] - 1e-8
        )


if __name__ == "__main__":
    unittest.main()
