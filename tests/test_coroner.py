import csv
import io
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "backtest-coroner" / "scripts"))
import coroner  # noqa: E402


def write_trades(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def coin_trades(n, p_win, rr=2.0, cost=0.05, start=date(2010, 1, 4), seed=1):
    rng = random.Random(seed)
    rows, d = [], start
    for _ in range(n):
        rows.append({"date": d.isoformat(), "gross": rr if rng.random() < p_win else -1.0, "cost": cost})
        d += timedelta(days=1 if d.weekday() < 4 else 3)
    return rows


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = coroner.main(argv)
    return code, buf.getvalue()


class Stats(unittest.TestCase):
    def test_c_star_matches_formula(self):
        g = [1.0, -1.0, 2.0, -1.0, 0.5] * 20
        n = len(g)
        expected = coroner.mean(g) - 3.0 * coroner.sd(g) / n ** 0.5
        self.assertAlmostEqual(coroner.c_star(g, 3.0), expected)

    def test_max_drawdown_is_continuous(self):
        self.assertEqual(coroner.max_drawdown([1, -2, 1, -3, 5]), -4)

    def test_null_centres_on_minus_cost(self):
        trades = [coroner.Trade(date(2020, 1, 1), g, 0.05, g - 0.05) for g in [2.0, -1.0] * 500]
        null = coroner.random_direction_null(trades, 400, random.Random(3))
        self.assertAlmostEqual(coroner.mean(null), -0.05, delta=0.01)


class Autopsy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_zero_edge_is_dead(self):
        p = self.dir / "t.csv"
        write_trades(p, coin_trades(3000, 1 / 3))
        code, out = run(["autopsy", str(p), "--seeds", "300"])
        self.assertEqual(code, 1)
        self.assertIn("verdict: DEAD", out)

    def test_strong_edge_over_long_history_is_alive(self):
        p = self.dir / "t.csv"
        write_trades(p, coin_trades(4000, 0.40))
        code, out = run(["autopsy", str(p), "--seeds", "300"])
        self.assertIn("ALIVE", out)
        self.assertEqual(code, 0)

    def test_too_few_trades_is_void(self):
        p = self.dir / "t.csv"
        write_trades(p, coin_trades(20, 0.6))
        _, out = run(["autopsy", str(p), "--seeds", "50"])
        self.assertIn("verdict: VOID", out)


class Prop(unittest.TestCase):
    def test_static_floor_blows_account(self):
        rules = coroner.PropRules(balance=100_000, risk=0.05, targets=[0.5], max_dd=0.10,
                                  dd_type="static", daily_loss=None, min_days=0, min_win_days=0,
                                  min_win_amount=0.01, fee=100, payout_at=0.03, split=0.8)
        d0 = date(2020, 1, 1)
        days = [(d0 + timedelta(days=i), [coroner.Trade(d0, -1.0, 0.0, -1.0)]) for i in range(3)]
        st, _ = coroner.run_program(days, rules)
        self.assertEqual(st["blown"], 1)          # equity 95k, 90k (= floor, not below), then 85k < floor
        self.assertEqual(st["attempts"], 1)

    def test_payout_resets_balance(self):
        rules = coroner.PropRules(balance=100_000, risk=0.01, targets=[], max_dd=0.10,
                                  dd_type="static", daily_loss=None, min_days=0, min_win_days=0,
                                  min_win_amount=0.01, fee=100, payout_at=0.03, split=0.8)
        d0 = date(2020, 1, 1)
        days = [(d0 + timedelta(days=i), [coroner.Trade(d0, 4.0, 0.0, 4.0)]) for i in range(2)]
        st, _ = coroner.run_program(days, rules)
        self.assertEqual(st["payouts"], 2)
        self.assertAlmostEqual(st["withdrawn"], 2 * 4000 * 0.8)


class Inject(unittest.TestCase):
    def test_drift_starts_after_signal_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "p.csv", Path(tmp) / "o.csv"
            rows = [{"time": i, "open": 100, "high": 101, "low": 99, "close": 100,
                     "signal": 1 if i == 2 else 0} for i in range(10)]
            write_trades(src, rows)
            run(["inject", str(src), "--out", str(out), "--drift", "4", "--bars", "4"])
            with open(out, newline="") as f:
                closes = [float(r["close"]) for r in csv.DictReader(f)]
            self.assertEqual(closes[:3], [100, 100, 100])     # signal bar untouched: no lookahead
            self.assertEqual(closes[3:7], [101, 102, 103, 104])
            self.assertEqual(closes[7:], [104, 104, 104])


if __name__ == "__main__":
    unittest.main()
