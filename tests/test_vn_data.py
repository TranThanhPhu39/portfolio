import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.portfolio.vn_data import load_periods


class VNDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.frame = pd.DataFrame(
            {
                "Ticker": ["A"] * 3,
                "Date": ["31/01/2020", "29/02/2020", "31/03/2020"],
                "Close (EOM)": ["1,000", "1,100", "990"],
                "Monthly Return (%)": [0, 10, -10],
                "rRF": [12] * 3,
                "VN30": [0, 2, -2],
            }
        )

    def load(self, **kwargs):
        self.frame.to_csv(self.path / "Top100_Ky01.csv", index=False)
        return load_periods(self.path, **kwargs)

    def test_annual_percent_conversion_and_returns(self):
        returns, _, risk_free, benchmark, _ = self.load()
        self.assertAlmostEqual(returns.iloc[1, 0], 0.1)
        self.assertAlmostEqual(risk_free.iloc[0], 1.12 ** (1 / 12) - 1)
        self.assertAlmostEqual(benchmark.iloc[1], 0.02)

    def test_prices_no_forward_fill(self):
        self.frame.loc[1, "Close (EOM)"] = np.nan
        returns, *_ = self.load(return_basis="prices")
        self.assertTrue(returns.isna().all().all())

    def test_first_price_month_not_counted_as_return(self):
        returns, membership, *_ = self.load(return_basis="prices")
        self.assertEqual(len(returns), 2)
        self.assertTrue(returns.index.equals(membership.index))
        self.assertAlmostEqual(returns.iloc[0, 0], 0.1)

    def test_partial_month_rejected(self):
        self.frame.loc[2, "Date"] = "25/03/2020"
        with self.assertRaisesRegex(ValueError, "non-month-end"):
            self.load(end="2020-03")

    def test_duplicate_rejected(self):
        self.frame = pd.concat([self.frame, self.frame.iloc[:1]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.load()

    def test_conflicting_rf_rejected(self):
        extra = self.frame.iloc[:1].copy()
        extra["Ticker"] = "B"
        extra["rRF"] = 4
        self.frame = pd.concat([self.frame, extra], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.load()


if __name__ == "__main__":
    unittest.main()
