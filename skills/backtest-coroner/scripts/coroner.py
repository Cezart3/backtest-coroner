#!/usr/bin/env python3
"""backtest-coroner: find out how your backtest died before your money does.

Standard library only. Four subcommands:

  autopsy    eras, holdout decay, breakeven cost c*, random-direction placebo,
             continuous max drawdown, implausibility check  -> death certificate
  prop       run a prop-firm account program over your trade history and compare
             it with the same program trading random direction (the real null)
  inject     plant a known edge into a price series, to prove your pipeline can
             see one (a negative result means nothing until this passes)
  breakeven  win rate needed for a fixed reward:risk bracket after cost

Trades CSV columns (case-insensitive):
  date            required, YYYY-MM-DD (a timestamp is fine, the date part is used)
  gross           per-trade result BEFORE cost, any unit (R multiples recommended)
  cost            per-trade cost, same unit, positive number
  net             optional if gross is given (net = gross - cost)
  mae, mfe        optional, R units: worst / best excursion inside the trade
                  (mae <= 0, mfe >= 0); used by `prop` for intraday breaches
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

T_GATE = 3.0          # default t gate for c*; a family-level bar, not a single-test bar
SIGMA2_PCT = 97.725   # one-sided 2 sigma, as a percentile


@dataclass
class Trade:
    d: date
    gross: float
    cost: float
    net: float
    mae: float | None = None
    mfe: float | None = None


def die(msg: str) -> None:
    sys.exit(f"coroner: {msg}")


def parse_date(s: str) -> date:
    s = s.strip()
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        die(f"cannot parse date {s!r}; use YYYY-MM-DD")


def _num(row: dict, key: str | None) -> float | None:
    if key is None:
        return None
    v = (row.get(key) or "").strip()
    return float(v) if v else None


def load_trades(path: str) -> tuple[list[Trade], list[str]]:
    warnings = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = {c.strip().lower(): c for c in (reader.fieldnames or [])}
        if "date" not in cols:
            die("trades CSV needs a 'date' column")
        g_key, c_key, n_key = cols.get("gross"), cols.get("cost"), cols.get("net")
        if g_key is None and n_key is None:
            die("trades CSV needs 'gross' (+ 'cost') or 'net'")
        if c_key is None:
            warnings.append("no 'cost' column: cost assumed 0, so c* and the placebo "
                            "treat your numbers as gross. Validate a cost model first (rule 4).")
        trades = []
        for row in reader:
            d = parse_date(row[cols["date"]])
            g, c, n = _num(row, g_key), _num(row, c_key) or 0.0, _num(row, n_key)
            if g is None and n is None:
                continue
            if g is None:
                g = n + c
            if n is None:
                n = g - c
            trades.append(Trade(d, g, c, n, _num(row, cols.get("mae")), _num(row, cols.get("mfe"))))
    if not trades:
        die("no trades loaded")
    trades.sort(key=lambda t: t.d)
    return trades, warnings


# ---------------------------------------------------------------- statistics

def mean(xs):
    return statistics.fmean(xs) if xs else 0.0


def sd(xs):
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def tstat(xs):
    s = sd(xs)
    return mean(xs) / s * math.sqrt(len(xs)) if s > 0 else 0.0


def years_span(trades):
    return max((trades[-1].d - trades[0].d).days / 365.25, 1 / 12)


def max_drawdown(xs):
    peak = cum = worst = 0.0
    for x in xs:
        cum += x
        peak = max(peak, cum)
        worst = min(worst, cum - peak)
    return worst


def c_star(gross, t_gate):
    """Highest mean cost per trade at which the gross stream still clears t_gate."""
    n = len(gross)
    return mean(gross) - t_gate * sd(gross) / math.sqrt(n) if n > 1 else float("nan")


def percentile_of(value, dist):
    below = sum(1 for x in dist if x < value)
    ties = sum(1 for x in dist if x == value)
    return 100.0 * (below + 0.5 * ties) / len(dist)


def random_direction_null(trades, seeds, rng):
    """Mean net per trade when every trade's direction is a coin flip and cost is still paid."""
    g = [t.gross for t in trades]
    c = [t.cost for t in trades]
    n = len(g)
    out = []
    for _ in range(seeds):
        bits = format(rng.getrandbits(n), f"0{n}b")
        total = 0.0
        for i in range(n):
            total += (g[i] if bits[i] == "1" else -g[i]) - c[i]
        out.append(total / n)
    return out


def split_eras(trades, spec):
    if spec:
        eras = []
        for part in spec.split(","):
            a, _, b = part.strip().partition("-")
            lo, hi = int(a), int(b or a)
            eras.append((f"{lo}-{hi}", [t for t in trades if lo <= t.d.year <= hi]))
        return eras
    d0, d1 = trades[0].d.toordinal(), trades[-1].d.toordinal() + 1
    step = (d1 - d0) / 3
    eras = []
    for k in range(3):
        lo, hi = d0 + k * step, d0 + (k + 1) * step
        chunk = [t for t in trades if lo <= t.d.toordinal() < hi]
        label = f"{date.fromordinal(int(lo))}..{date.fromordinal(int(hi) - 1)}"
        eras.append((label, chunk))
    return eras


# ---------------------------------------------------------------- autopsy

def autopsy(args):
    trades, warnings = load_trades(args.trades)
    rng = random.Random(args.seed)
    n = len(trades)
    gross = [t.gross for t in trades]
    net = [t.net for t in trades]
    cost_paid = mean([t.cost for t in trades])
    yrs = years_span(trades)
    per_year = n / yrs
    sharpe = (mean(net) / sd(net) * math.sqrt(per_year)) if sd(net) > 0 else 0.0
    cs = c_star(gross, args.t_gate)

    findings = []   # (severity, rule, text); severity: DEAD | SUSPECT | NOTE

    def add(sev, rule, text):
        findings.append((sev, rule, text))

    print(f"\nBACKTEST CORONER - autopsy of {args.trades}")
    print("=" * 72)
    print(f"trades {n}   span {trades[0].d} .. {trades[-1].d} ({yrs:.1f} y)   "
          f"{per_year:.0f} trades/y")
    print(f"gross/trade {mean(gross):+.4f}   cost/trade {cost_paid:.4f}   "
          f"net/trade {mean(net):+.4f}")
    print(f"t(net) {tstat(net):+.2f}   t(gross) {tstat(gross):+.2f}   "
          f"annualised Sharpe {sharpe:+.2f}   continuous maxDD {max_drawdown(net):+.2f}")

    if n < 30:
        add("DEAD", "VOID", f"{n} trades: too few to support any verdict. Status VOID, not PASS.")

    # breakeven cost inversion (rule 15)
    print(f"\nbreakeven cost c* (t gate {args.t_gate:g}): {cs:+.4f} per trade, you pay {cost_paid:.4f}")
    if cs < 0:
        add("DEAD", "15", f"c* = {cs:+.4f} < 0: fails the t gate even at ZERO cost. "
                          "No broker, venue or rebate fixes a missing signal.")
    elif cs < cost_paid:
        add("DEAD", "15", f"cost-killed: survives only if cost <= {cs:.4f}, you pay {cost_paid:.4f}.")

    # eras (rules 1, 26)
    eras = split_eras(trades, args.eras)
    print("\nera                        n     gross     net      t(net)  years+")
    alive_eras = 0
    for label, chunk in eras:
        if not chunk:
            print(f"{label:24s} {0:5d}   (empty)")
            continue
        yr = defaultdict(float)
        for t in chunk:
            yr[t.d.year] += t.net
        pos = sum(1 for v in yr.values() if v > 0)
        tn = tstat([t.net for t in chunk])
        alive_eras += tn >= 2.0
        print(f"{label:24s} {len(chunk):5d}  {mean([t.gross for t in chunk]):+.4f}  "
              f"{mean([t.net for t in chunk]):+.4f}  {tn:+6.2f}   {pos}/{len(yr)}")
    counts = [len(c) for _, c in eras]
    if min(counts) and max(counts) / min(counts) > 4:
        add("SUSPECT", "26", f"trade count per era ranges {min(counts)}..{max(counts)}: "
                             "check coverage per year before comparing eras (a monotone ramp = "
                             "survivorship confounded with era).")
    neg_eras = sum(1 for _, c in eras if c and mean([t.net for t in c]) <= 0)
    if alive_eras == 1 and neg_eras >= 1:
        add("DEAD", "1", "the edge lives in ONE era and is flat/negative in another. "
                         "Same-era holdouts cannot see this; out-of-era data will.")
    if yrs < 6:
        add("SUSPECT", "1", f"whole sample is {yrs:.1f} years = one market era. Any holdout cut "
                            "inside it is not a holdout. Add older data before trusting a PASS.")

    yearly = defaultdict(float)
    for t in trades:
        yearly[t.d.year] += t.net
    pos_years = sum(1 for v in yearly.values() if v > 0)
    print(f"\npositive years {pos_years}/{len(yearly)}: " +
          " ".join(f"{y}:{v:+.1f}" for y, v in sorted(yearly.items())))

    # holdout decay (F74: never size off in-sample expectancy)
    if args.holdout_from:
        cut = parse_date(args.holdout_from)
        is_, oos = [t for t in trades if t.d < cut], [t for t in trades if t.d >= cut]
        if is_ and oos:
            mi, mo = mean([t.net for t in is_]), mean([t.net for t in oos])
            ratio = (mi / mo) if mo > 0 else float("inf")
            print(f"\nholdout from {cut}: IS net {mi:+.4f} (n {len(is_)}, t {tstat([t.net for t in is_]):+.2f})"
                  f"   OOS net {mo:+.4f} (n {len(oos)}, t {tstat([t.net for t in oos]):+.2f})")
            if mo <= 0:
                add("DEAD", "1", f"holdout net {mo:+.4f} <= 0. In-sample t bought nothing.")
            elif ratio > 2:
                add("SUSPECT", "F74", f"in-sample expectancy is {ratio:.1f}x the holdout. Size and "
                                      "project ONLY from the holdout number.")
            if (oos[-1].d - oos[0].d).days < 365 * 2:
                add("NOTE", "1", "holdout shorter than 2 years: weak, and probably same era.")

    # random-direction placebo (rules 6, 28)
    null = random_direction_null(trades, args.seeds, rng)
    nm, ns = mean(null), sd(null)
    real = mean(net)
    z = (real - nm) / ns if ns > 0 else 0.0
    pct = percentile_of(real, null)
    print(f"\nrandom-direction placebo ({args.seeds} seeds, cost still paid): "
          f"null mean {nm:+.4f} sd {ns:.4f}  ->  real z {z:+.2f}, percentile {pct:.1f}%")
    if pct < SIGMA2_PCT:
        add("DEAD", "28", f"real result sits at the {pct:.1f}th percentile of coin-flip direction: "
                          "indistinguishable from random at 2 sigma (percentile rule).")
    if args.seeds < 2000:
        add("NOTE", "28", "fewer than 2,000 seeds cannot decide a 2-sigma threshold.")
    add("NOTE", "27", "placebo flips the sign of each trade's gross. If your stop/target geometry "
                      "depends on direction (stops at range edges), re-run the placebo inside your "
                      "engine with mirrored geometry and compare its trade count to the real one.")

    # implausibility (rule 3)
    if sharpe > 3:
        add("SUSPECT", "3", f"annualised Sharpe {sharpe:.2f} is implausible for retail execution. "
                            "Treat it as a bug report: lookahead, same-bar fills (rule 9), or a "
                            "learned sign applied to net instead of gross (rule 2).")
    for w in warnings:
        add("NOTE", "4", w)

    # verdict
    dead = [f for f in findings if f[0] == "DEAD"]
    suspect = [f for f in findings if f[0] == "SUSPECT"]
    if any(f[1] == "VOID" for f in dead):
        verdict = "VOID"
    elif dead:
        verdict = "DEAD"
    elif suspect:
        verdict = "SUSPECT"
    else:
        verdict = "ALIVE (provisional)"
    print("\n" + "=" * 72)
    print(f"DEATH CERTIFICATE   verdict: {verdict}")
    print("=" * 72)
    order = {"DEAD": 0, "SUSPECT": 1, "NOTE": 2}
    for sev, rule, text in sorted(findings, key=lambda f: order[f[0]]):
        print(f"[{sev:7s}] rule {rule:>4s}  {text}")
    if verdict.startswith("ALIVE"):
        print("\nStill owed before money: injection probe on your own engine (`inject`), "
              "a pre-registered holdout from another era, and `prop` if this goes on a funded account.")
    return 0 if verdict.startswith("ALIVE") else 1


# ---------------------------------------------------------------- prop account program

@dataclass
class PropRules:
    balance: float
    risk: float
    targets: list[float]
    max_dd: float
    dd_type: str
    daily_loss: float | None
    min_days: int
    min_win_days: int
    min_win_amount: float
    fee: float
    payout_at: float
    split: float


def run_program(days, rules, rng=None, use_excursions=False):
    """One continuous account program over the whole history: buy, evaluate, get funded,
    withdraw, and re-buy after every blown account. rng=None trades the real direction;
    otherwise every trade's direction is a coin flip (cost still paid)."""
    B = rules.balance
    risk_usd = rules.risk * B
    st = {"fees": 0.0, "withdrawn": 0.0, "payouts": 0, "attempts": 0, "funded": 0, "blown": 0}
    yearly = defaultdict(float)
    acct = None

    def buy(year):
        st["fees"] += rules.fee
        st["attempts"] += 1
        yearly[year] -= rules.fee
        if not rules.targets:
            st["funded"] += 1
        return {"phase": 0, "bal": B, "peak": B, "days": 0, "wins": 0}

    def floor(a):
        static = B * (1 - rules.max_dd)
        if rules.dd_type == "static":
            return static
        return min(a["peak"] - rules.max_dd * B, B)   # trailing floor locks at the start balance

    for d, trades in days:
        if acct is None:
            acct = buy(d.year)
        a = acct
        day_start = a["bal"]
        blown = False
        for t in trades:
            flip = rng is not None and rng.random() < 0.5
            r = (-t.gross if flip else t.gross) - t.cost
            if use_excursions:
                adverse = -(t.mfe or 0.0) if flip else (t.mae or 0.0)
                favour = -(t.mae or 0.0) if flip else (t.mfe or 0.0)
            else:
                adverse, favour = min(r, 0.0), max(r, 0.0)
            low = a["bal"] + min(adverse, r, 0.0) * risk_usd
            if rules.dd_type == "trailing":
                a["peak"] = max(a["peak"], a["bal"] + favour * risk_usd)
            if low < floor(a) or (rules.daily_loss and low < day_start - rules.daily_loss * B):
                blown = True
                break
            a["bal"] += r * risk_usd
            if rules.dd_type == "trailing":
                a["peak"] = max(a["peak"], a["bal"])
        if blown:
            st["blown"] += 1
            acct = None
            continue
        if not trades:
            continue
        a["days"] += 1
        if a["bal"] - day_start >= rules.min_win_amount:
            a["wins"] += 1
        if rules.dd_type == "eod_trailing":
            a["peak"] = max(a["peak"], a["bal"])
        if a["phase"] < len(rules.targets):
            if (a["bal"] >= B * (1 + rules.targets[a["phase"]]) and a["days"] >= rules.min_days
                    and a["wins"] >= rules.min_win_days):
                a.update(phase=a["phase"] + 1, bal=B, peak=B, days=0, wins=0)
                if a["phase"] == len(rules.targets):
                    st["funded"] += 1
        else:
            profit = a["bal"] - B
            if profit >= rules.payout_at * B and a["wins"] >= rules.min_win_days:
                w = profit * rules.split
                st["withdrawn"] += w
                st["payouts"] += 1
                yearly[d.year] += w
                a.update(bal=B, peak=B, wins=0)
    st["net"] = st["withdrawn"] - st["fees"]
    return st, yearly


def prop(args):
    trades, warnings = load_trades(args.trades)
    by_day = defaultdict(list)
    for t in trades:
        by_day[t.d].append(t)
    days = sorted(by_day.items())
    use_exc = all(t.mae is not None and t.mfe is not None for t in trades)
    rules = PropRules(
        balance=args.balance, risk=args.risk,
        targets=[float(x) for x in args.targets.split(",") if x.strip()],
        max_dd=args.max_dd, dd_type=args.dd_type, daily_loss=args.daily_loss,
        min_days=args.min_days, min_win_days=args.min_win_days,
        min_win_amount=args.min_win_amount, fee=args.fee,
        payout_at=args.payout_at, split=args.split)
    months = max((trades[-1].d - trades[0].d).days / 30.44, 1.0)

    real, yearly = run_program(days, rules, None, use_exc)
    rng = random.Random(args.seed)
    nulls = [run_program(days, rules, rng, use_exc)[0]["net"] for _ in range(args.seeds)]
    nm, ns = mean(nulls), sd(nulls)
    z = (real["net"] - nm) / ns if ns > 0 else 0.0
    pct = percentile_of(real["net"], nulls)
    beats_fee = 100.0 * sum(1 for x in nulls if x > 0) / len(nulls)

    print(f"\nBACKTEST CORONER - prop account program on {args.trades}")
    print("=" * 72)
    print(f"account ${rules.balance:,.0f}  risk {rules.risk:.2%}/trade  targets "
          f"{'/'.join(f'{x:.0%}' for x in rules.targets) or 'none (instant funded)'}  "
          f"{rules.dd_type} DD {rules.max_dd:.0%}  daily loss "
          f"{f'{rules.daily_loss:.0%}' if rules.daily_loss else 'none'}  fee ${rules.fee:,.0f}")
    print(f"payout when profit >= {rules.payout_at:.0%}, split {rules.split:.0%}, balance resets "
          f"after payout   min days {rules.min_days}, min winning days {rules.min_win_days}")
    print(f"\nREAL      accounts bought {real['attempts']}  funded {real['funded']}  blown "
          f"{real['blown']}  payouts {real['payouts']}")
    print(f"          withdrawn ${real['withdrawn']:,.0f}  fees ${real['fees']:,.0f}  "
          f"NET ${real['net']:,.0f}  (${real['net'] / months:,.0f}/month over {months:.0f} months)")
    print("          by year: " + " ".join(f"{y}:{v:+,.0f}" for y, v in sorted(yearly.items())))
    print(f"\nNULL      random direction, same days, same cost, {args.seeds} seeds")
    print(f"          net mean ${nm:,.0f}  sd ${ns:,.0f}   null beats its fees in {beats_fee:.1f}% of seeds")
    print(f"          real z {z:+.2f}, percentile {pct:.1f}%")

    print("\n" + "=" * 72)
    lines = []
    if nm > 0:
        lines.append("[STRUCTURE] the account rules pay a coin flip on average (rule 29). Your bar is "
                     f"the null (${nm:,.0f}), not $0 - only the part above it is edge.")
    else:
        lines.append(f"[STRUCTURE] the account rules lose ${-nm:,.0f} on a coin flip: "
                     "only a real edge can pay here.")
    if pct >= SIGMA2_PCT:
        verdict = "EDGE OVER STRUCTURE (provisional)"
    elif real["net"] > 0:
        verdict = "PAYS, BUT NOT DISTINGUISHABLE FROM RANDOM DIRECTION"
    else:
        verdict = "DEAD"
    neg_years = sum(1 for v in yearly.values() if v < 0)
    if neg_years:
        lines.append(f"[REGIME] {neg_years}/{len(yearly)} calendar years lose money. Size is a bet "
                     "on regime (rule 30): never pick it on the forward era.")
    if args.seeds < 2000:
        lines.append("[NOTE] < 2,000 seeds cannot decide a 2-sigma call (rule 28).")
    if rules.dd_type != "static" and not use_exc:
        lines.append("[NOTE] trailing drawdown without mae/mfe columns: intraday breaches are "
                     "invisible, so this is OPTIMISTIC. Real paths whip through trailing floors.")
    lines.append("[NOTE] verify the firm's CURRENT terms: payout frequency limits, consistency "
                 "rules and bot bans can each erase the result.")
    print(f"PROP VERDICT: {verdict}")
    print("=" * 72)
    for line in lines + [f"[NOTE] {w}" for w in warnings]:
        print(line)
    return 0 if verdict.startswith("EDGE") else 1


# ---------------------------------------------------------------- inject

def inject(args):
    with open(args.prices, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    cols = {c.strip().lower(): c for c in fields}
    for need in ("open", "high", "low", "close", "signal"):
        if need not in cols:
            die(f"prices CSV needs '{need}' (signal: +1 long / -1 short / 0 on each bar)")
    o, h, l, c, s = (cols[k] for k in ("open", "high", "low", "close", "signal"))
    n = len(rows)
    ohlc = [[float(r[o]), float(r[h]), float(r[l]), float(r[c])] for r in rows]
    sig = [int(float(r[s] or 0)) for r in rows]

    atr = [0.0] * n
    trs = []
    for i in range(n):
        prev = ohlc[i - 1][3] if i else ohlc[i][3]
        trs.append(max(ohlc[i][1] - ohlc[i][2], abs(ohlc[i][1] - prev), abs(ohlc[i][2] - prev)))
        window = trs[max(0, i - 13): i + 1]
        atr[i] = sum(window) / len(window)

    # per-bar drift increments; drift starts AFTER the signal bar so capturing it needs no lookahead
    inc = [0.0] * (n + args.bars + 2)
    events = 0
    for i, sg in enumerate(sig):
        if sg == 0:
            continue
        events += 1
        size = args.drift if args.drift is not None else args.drift_atr * atr[i]
        step = sg * size / args.bars
        for k in range(args.start, args.start + args.bars):
            if i + k < n:
                inc[i + k] += step
    offset = 0.0
    for i in range(n):
        offset += inc[i]
        rows[i][o], rows[i][h], rows[i][l], rows[i][c] = (f"{v + offset:.10g}" for v in ohlc[i])
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    unit = f"{args.drift:g} price units" if args.drift is not None else f"{args.drift_atr:g} x ATR(14)"
    print(f"planted {unit} of drift after each of {events} signal bars, spread over {args.bars} "
          f"bars starting {args.start} bar(s) after the signal -> {args.out}")
    print("Now run YOUR unchanged backtest on this file (probe S). It must show a clearly positive "
          "gross on the signal trades. Also run: probe R (original file reproduces your published "
          "numbers exactly) and probe C (cost x10 must cut net by ~9x your base cost).")
    print("If the planted edge does not come out, your pipeline destroys edges and every negative "
          "result it produced is meaningless (rule 8b).")
    return 0


# ---------------------------------------------------------------- breakeven

def breakeven(args):
    p = (1 + args.cost) / (1 + args.rr)
    print(f"bracket {args.rr:g}R target : 1R stop, cost {args.cost:g}R/trade -> breakeven win rate {p:.2%}")
    if args.winrate is not None:
        ev = args.winrate * args.rr - (1 - args.winrate) - args.cost
        print(f"at win rate {args.winrate:.2%}: expectancy {ev:+.4f} R/trade")
    print("This is the PER-TRADE breakeven. A prop account needs more: trailing floors, daily loss "
          "limits and payout gates raise it (run `prop`).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="coroner", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("autopsy", help="death certificate for a trades CSV")
    a.add_argument("trades")
    a.add_argument("--eras", help="year ranges, e.g. 2010-2015,2016-2020,2021-2026 (default: 3 equal spans)")
    a.add_argument("--holdout-from", help="YYYY-MM-DD; trades on/after are the holdout")
    a.add_argument("--t-gate", type=float, default=T_GATE)
    a.add_argument("--seeds", type=int, default=2000)
    a.add_argument("--seed", type=int, default=7)
    a.set_defaults(fn=autopsy)

    p = sub.add_parser("prop", help="prop account program vs random-direction null")
    p.add_argument("trades", help="trades CSV in R units (gross + cost recommended)")
    p.add_argument("--balance", type=float, default=100_000)
    p.add_argument("--risk", type=float, default=0.01, help="fraction of start balance risked per 1R")
    p.add_argument("--targets", default="0.08,0.05", help="evaluation phase targets, comma separated ('' = none)")
    p.add_argument("--max-dd", type=float, default=0.10)
    p.add_argument("--dd-type", choices=["static", "trailing", "eod_trailing"], default="static")
    p.add_argument("--daily-loss", type=float, default=0.05, help="fraction of start balance; 0 = none")
    p.add_argument("--min-days", type=int, default=0, help="min trading days per evaluation phase")
    p.add_argument("--min-win-days", type=int, default=0, help="min winning days per phase / payout")
    p.add_argument("--min-win-amount", type=float, default=0.01, help="USD for a day to count as winning")
    p.add_argument("--fee", type=float, default=540)
    p.add_argument("--payout-at", type=float, default=0.03, help="withdraw when profit >= this fraction")
    p.add_argument("--split", type=float, default=0.80)
    p.add_argument("--seeds", type=int, default=2000)
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(fn=prop)

    i = sub.add_parser("inject", help="plant a known edge into a price CSV")
    i.add_argument("prices")
    i.add_argument("--out", required=True)
    g = i.add_mutually_exclusive_group(required=True)
    g.add_argument("--drift", type=float, help="total drift per event, price units")
    g.add_argument("--drift-atr", type=float, help="total drift per event, in ATR(14) at the signal bar")
    i.add_argument("--bars", type=int, default=12, help="bars the drift is spread over")
    i.add_argument("--start", type=int, default=1, help="bars after the signal bar where drift begins")
    i.set_defaults(fn=inject)

    b = sub.add_parser("breakeven", help="breakeven win rate for a fixed bracket")
    b.add_argument("--rr", type=float, required=True, help="target in R (stop = 1R)")
    b.add_argument("--cost", type=float, default=0.0, help="cost per trade in R")
    b.add_argument("--winrate", type=float)
    b.set_defaults(fn=breakeven)

    args = ap.parse_args(argv)
    if getattr(args, "daily_loss", None) == 0:
        args.daily_loss = None
    if getattr(args, "bars", 1) < 1:
        die("--bars must be >= 1")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
