"""Generate the SYNTHETIC demo backtests used in the README. No real market data.

The story: a breakout strategy with a 2R target that has a real edge only in 2021-2024
and none before. Backtested on recent data alone it looks like a winner; the full history
shows what it is.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
RR, COST = 2.0, 0.05


def win_prob(d: date) -> float:
    # expectancy = 3p - 1 at RR 2: p 0.3833 -> +0.15R gross, p 1/3 -> 0
    return 0.3833 if 2021 <= d.year <= 2024 else 1 / 3


def main(seed: int = 11) -> None:
    rng = random.Random(seed)
    rows = []
    d = date(2010, 1, 4)
    while d <= date(2025, 12, 31):
        if d.weekday() < 5 and rng.random() < 0.9:
            if rng.random() < win_prob(d):
                gross, mae, mfe = RR, -rng.uniform(0.05, 0.95), RR
            else:
                gross, mae, mfe = -1.0, -1.0, rng.uniform(0.0, 1.9)
            rows.append({"date": d.isoformat(), "gross": gross, "cost": COST,
                         "mae": round(mae, 3), "mfe": round(mfe, 3)})
        d += timedelta(days=1)

    for name, keep in (("full_history.csv", lambda r: True),
                       ("recent_only.csv", lambda r: r["date"] >= "2021-01-01" and r["date"] < "2025-01-01")):
        with open(HERE / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "gross", "cost", "mae", "mfe"])
            w.writeheader()
            w.writerows(r for r in rows if keep(r))
    print("wrote full_history.csv and recent_only.csv (synthetic)")


if __name__ == "__main__":
    main()
