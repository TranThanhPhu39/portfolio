import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from create_sample_inputs import create
from run_backtest import execute, read_monthly


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        create(self.root)
        config_path = Path(__file__).resolve().parents[1] / "config/example.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.config.update(
            returns="returns.csv",
            benchmark="benchmark.csv",
            risk_free="risk_free.csv",
            output_dir="result",
        )

    def run_config(self):
        path = self.root / "config.json"
        path.write_text(json.dumps(self.config), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            return execute(path)

    def test_two_strategies_full_export_and_no_overwrite(self):
        self.config["strategies"]["DEMO_second_adapter"] = (
            "demo_synthetic:equal_weight_demo"
        )
        output = self.run_config()
        table = pd.read_csv(output / "comparison.csv")
        self.assertEqual(len(table), 10)
        self.assertEqual(set(table.months), {59})
        self.assertEqual(len(list(output.glob("*_periods.csv"))), 8)
        self.assertTrue((output / "report.html").exists())
        self.assertTrue((output / "sharpe_vs_fee.svg").exists())
        metadata = json.loads((output / "run_metadata.json").read_text())
        self.assertEqual(len(metadata["input_sha256"]["returns"]), 64)
        with self.assertRaises(FileExistsError):
            self.run_config()

    def test_builtin_optimizers_real_runner_connection(self):
        self.config["ridge"] = 1e-8
        self.config["strategies"] = {
            "MinVariance": "builtin:min_variance",
            "MaxSharpe": "builtin:max_sharpe",
            "EqualWeight": "builtin:equal_weight",
        }
        output = self.run_config()
        table = pd.read_csv(output / "comparison.csv")
        self.assertEqual(len(table), 15)
        self.assertEqual(
            set(table.strategy), {"MinVariance", "MaxSharpe", "EqualWeight"}
        )
        self.assertTrue((output / "05_sharpe_assets_comparison.csv").exists())

    def test_duplicate_input_rejected(self):
        path = self.root / "returns.csv"
        frame = pd.read_csv(path)
        pd.concat([frame, frame.iloc[:1]]).to_csv(path, index=False)
        with self.assertRaises(ValueError):
            read_monthly(path, ["date", "ticker", "return"])

    def test_missing_rf_fails_before_export(self):
        path = self.root / "risk_free.csv"
        pd.read_csv(path).iloc[:-1].to_csv(path, index=False)
        with self.assertRaises(ValueError):
            self.run_config()
        self.assertFalse((self.root / "result").exists())

    def test_dynamic_universe_rejected(self):
        self.config["universe_mode"] = "historical"
        with self.assertRaises(ValueError):
            self.run_config()

    def test_required_fee_scenarios(self):
        self.config["rates"] = [0]
        with self.assertRaises(ValueError):
            self.run_config()

    def test_non_month_end_rejected(self):
        path = self.root / "benchmark.csv"
        frame = pd.read_csv(path)
        frame.loc[0, "date"] = "2017-01-15"
        frame.to_csv(path, index=False)
        with self.assertRaises(ValueError):
            self.run_config()


if __name__ == "__main__":
    unittest.main()
