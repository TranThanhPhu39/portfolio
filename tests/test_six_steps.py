import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from run_six_steps import run


class Stage6Integration(unittest.TestCase):
    def test_all_stages_and_three_strategies(self):
        with tempfile.TemporaryDirectory() as temporary:
            with contextlib.redirect_stdout(io.StringIO()):
                output = run(Path(temporary) / "results")
            for filename in [
                "01_monthly_returns.csv",
                "02_expected_returns.csv",
                "03_weights.csv",
                "04_frontier.svg",
                "05_in_sample_comparison.csv",
                "06_comparison.csv",
                "report.html",
            ]:
                self.assertTrue((output / filename).is_file(), filename)
            table = pd.read_csv(output / "06_comparison.csv")
            self.assertEqual(
                set(table.strategy), {"MinVariance", "MaxSharpe", "EqualWeight"}
            )
            self.assertEqual(len(table), 15)
            self.assertEqual(set(table.months), {59})
            self.assertEqual(len(list(output.glob("06_*_trades.csv"))), 12)
            scores = pd.read_csv(output / "05_sharpe_assets_comparison.csv")
            self.assertEqual(len(scores), 6)
            self.assertIn("Sharpe từng mã", (output / "report.html").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
