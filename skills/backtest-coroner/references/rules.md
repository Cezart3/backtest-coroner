# The rules, with the number that produced each one

Each rule was paid for by a strategy family that failed (family IDs F16-F99). Numbers are from
real measurements on index futures/CFDs (NQ, ES, YM, US30, NAS100), FX, US equities and ETFs,
2010-2026 unless stated. Quote the number when you apply the rule.

---

## Part I: Measurement rules

### 1. A holdout in the same era as the in-sample is not a holdout
Two unrelated strategies (an opening range breakout and a VWAP strategy), with no shared signal,
exit or target, shared only the **measurement window 2021-2024**, and both showed an edge
*only* there. Gross by era, ORB: −0.071 / +0.016 / **+0.120** R; VWAP: negative / ~0 / **+0.067**.
**t = +3.73 over 4 in-sample years bought exactly zero over 10.5 unseen years.**
→ A holdout must come from a different market era. Recent-only data can fail a strategy, never
pass one.

### 2. A learned sign multiplies gross only; subtract cost afterwards
`sign(mean_IS)` applied to the **net** stream also flips the cost. A momentum cell is the exact
mirror of its reversal twin at gross, but both pay positive cost, so the pair averages out cost
free, and where the loser is more negative the cost enters as profit. It produced a false PASS
on all six gates: **Sharpe 3.79 / 4.71, 19/19 positive holdout years.**
```python
kept.append(sign * s["gross"] - s["cost"])   # never: sign * s["net"]
```

### 3. Implausibility is a debugging signal, not a discovery
Corollary of 2. Sharpe 4 on a daily strategy is not credible. The rule-2 bug was found
*because* the result was too good.

### 4. Validate the cost model on a known truth before using it as a gate
Corwin-Schultz overstated NQ's measured spread **29.2×** (31.19 vs 1.07 bps), and the error grows
with volatility, exactly where its assumption breaks. Replaced with structural
`S = tick/price × m(ADV)`, m = 1/2/4 at ADV thresholds of $50M and $10M.

### 5. The era's tick size is not a detail
US equity tick: 1/8 until 1997-06-24, 1/16 until 2001-04-09, $0.01 after. Measured intraday
round trip: SPY **10.39 bps** (1994-2004) / 1.28 / 0.81; single stock **38.0 bps** (1996-2006) /
5.2 / 2.3. A pre-2001 backtest with a 1-cent tick understates its cost 10-16×.

### 6. Carry a lookahead control (must fire) and a placebo (must not)
Costs almost nothing and turns every negative from "maybe I measured wrong" into "apparatus
verified both ways". Example lookahead control: sorting on the session's own return →
**t +94.53, Sharpe +20.21**. It must come out huge; if it does not, the engine is broken.

### 7. The placebo must vary exactly the dimension under test
Testing a *day* effect by shifting the calendar 6 weeks degenerated: for a cell selecting 50% of
days, shifting changes almost nothing, so the placebo re-measured the unconditional mean
(|t| 4.27 false positive). Testing a *name* effect by swapping each name for the nearest
non-event name by liquidity rank discriminated correctly. **Change the entity, not the date,
when the entity is the hypothesis.**

### 8. Evaluate the apparatus gate BEFORE any cell
A run stopped at its data-density gate (declared ≥100 events per session, real median 5) before
any cell was computed, so the construction could be fixed blind. A control evaluated at the end
cannot do that without contaminating the verdict. Gate fails are NULL, not FAIL.

### 8b. Controls guard against false positives; only injection guards against false negatives
A bug that **destroys** a real edge produces a result identical to an honest negative, and no
control flags it. Plant an edge of known size upstream of all aggregation and check it comes out
at the right size. Three probes with known answers:
- **R** no injection → must reproduce the published result exactly;
- **S** `alpha × sign(cell IS mean)` → fitted signs unchanged, so recovery must be exactly `+alpha`;
- **C** cost × 10 → net must fall by ~9× the base cost (regression test for rule 2).

On a portfolio study: S recovered **+5.00 of +5.00** bps; power statement: a 5 bps/day edge would
have read t +4.22 / +5.80 on the holdouts; they read −1.12 / −3.53, so the negative was real.
On the highest-stakes negative (an ORB falsification) a continuation drift planted exactly at the
breakout bar came out at **t +24.87, 11/11 years positive** at one range-width of drift. Real data:
3/11 years. **With a real edge, every year is positive.**
Path-dependent strategies (SL/TP) must be injected into the **price series** from the trigger bar
forward; injecting into returns puts lookahead in the probe itself.

### 8c. An audit probe must respect what the code does
A first probe added `+alpha` uniformly and "failed" a healthy pipeline: a sign-fitting aggregator
subtracts the injection on cells signed −1, so correct recovery is `(2p − 1)·alpha` (1.21 of 5.00
at p = 0.62). A badly designed probe produces a false negative about false negatives.

### 9. Limit-entry strategies must be resolved on data finer than the signal bar
A limit fills on one extreme of a bar; scoring the exit on the other extreme of the same bar
fabricates profit. Measured: **78.6% same-bar trades, 71.7% of wins had the target printed BEFORE
the entry.** The "universal 13/13 instruments" edge was the artifact; on the real M1 path net
was −0.01 on NQ. (A grid will also choose the tightest stop, because it maximises the artifact.)

### 10. Stops in ATR units, never fixed points
Cost is fixed in dollars, risk is in points, so a fixed stop is a different strategy in every era.
The same ATR-scaled M1 scalp on NQ cost **0.498 R in 2010 and 0.046 R in 2025** (10.8× less),
because the index rose 13×, not because fees fell.

### 11. Always report continuous max drawdown
Monthly-reset drawdown is fiction. A combination that looked fine on monthly DD had a real
continuous DD of −25%.

### 12. An unreproducible selection rule can support only a FAIL, never a PASS
60% of a "stocks in play" list could not be found in any reconstructible candidate pool. The
verdict closed as **undecidable**, not negative.

### 13. Bonferroni on signal sets, not on cells
Discounting "sister cells" is invalid across exit variants: those are different strategies, not
the same one measured many times.

### 14. Carry the region, never the grid max
`Spearman(IS rank, OOS rank) = −0.087`. In-sample rank holds no information about out-of-sample
rank. If a parameter region is not good as a block, its peak is noise.

### 21. A tail that goes the wrong way is the signature of a non-mechanism
If a signal is real, concentrating on its extremes must **strengthen** it. When gross falls or
flips as the book gets more extreme, what remains in the broad book is diffuse noise. Daily short
volume: broad rank book +0.85 / +0.14 / +1.29 bps/day, but top-20 −1.16 / −0.22 / −1.45 and top-10
−1.02 / −0.54 / −2.55, monotone inverted in all three eras.

### 22. Order-flow information is contemporaneous, not predictive
Same data, same book: **contemporaneous** short volume t −61.51, **tradeable** (prior session)
t +1.76. Monetising a contemporaneous relation requires being faster than it: a latency race,
not a research problem.

---

## Part II: Tools that save whole families

### 15. Breakeven-cost inversion
Net t is linear in cost, so
```
c* = g − T·s/√n          (t gate T, per-trade gross mean g, sd s, n trades)
c* = g − S·s/√252        (Sharpe gate S, daily)
```
c* is the cost the candidate could bear and still clear the gate. **c* below the cost already
paid: no broker fixes it. c* negative: it fails at zero cost.** A pre-FOMC calendar structure was
+12/12 consistent, the most stable structure ever found, and c* was negative in all 15 cells;
the follow-up family was never written. A 44-candidate seasonality screen closed for the price
of one script.

### 16. The kill-only screen
When a class has many cheap candidates, run a cost screen declared **in advance** as able only to
kill, never to validate. Multiple comparisons guarantee some candidates look good by chance.

### 17. Return at fixed drawdown ∝ Sharpe², and the basis matters
Validated directly with 1.8% error (Sharpe 1.58 → 0.771%/month; 1.89 → 1.084; predicted 1.431 vs
observed 1.406). On per-trade annualised Sharpe for futures: constant 0.309, so **2%/month needs
Sharpe ≈ 2.54, 3%/month ≈ 3.12.** Never mix bases (a CFD-basis anchor once understated the
required Sharpe by 1.8×).

### 18. √k multiplies zero
Eight futures with correlation only 0.16: the diversification was there, the edge was not. Four
streams with mean ρ −0.05 in every era still lost on both holdouts. You cannot diversify
something that does not exist. Same for trade frequency: √N multiplies expectancy, and at
gross ≈ 0 no frequency helps (an HF scalp was negative **at zero cost**, best cell +0.0198 R at
t 1.87 across 245,000 trades).

### 19. IC stability is not PnL stability
IC is a rank correlation, so it is scale-free. An IC that looked identical in three eras hid a
payoff conditional on volatility: 2008 +66.8%, 2020 +31.0%, every calm year negative. Never
call an IC stable without the yearly PnL next to it.

### 20. Day-trading-only is a cost multiplier
A weekly signal traded under "flat by close" pays a round trip **every day**: ~5× the cost of the
same information held a week (1× daily, ~5× weekly, ~21× monthly). Multiply cost by reopen
frequency and check c* before testing slow signals intraday. (Measured: removing the
constraint did not rescue those signals either; the binding cause was nonstationarity.)

---

## Part III: Later rules

### 23. A control must prove POWER before its null means anything
"The signal survives orthogonalisation against X" says nothing if X has no measurable power on
the **same universe and horizon**. A 5-day reversal control taken from the literature was empty on
the family's universe (gross +0.99 / −0.54 / +1.43 bps/day, |t| < 1.4, corr with the signal
+0.014…+0.059): the gate built on it passed a contentless comparison. Report the control's own
power on the family's data before it enters a protocol.

### 24. Rank books are fragile on rare, heavy-tailed signals
Projecting out a variable correlated only 0.03 cut gross 54-81%, unstably (retention −222% / 46% /
19%). Small correlation should mean a small, stable effect; rank weighting on dollar signals with
many near-ties reorders the book disproportionately. Report rank sensitivity, not just correlation.

### 25. Cost grows faster than signal down the liquidity ladder
One signal, one day, one book, only liquidity varies:

| ADV tier | gross | cost | net | c* |
|---|---|---|---|---|
| ≥ $50M | +11.61 | 2.62 | +8.99 | +2.95 |
| $10-50M | +13.06 | 8.75 | +4.30 | −0.53 |
| $1-10M | **+20.15** | **32.68** | **−12.53** | −19.50 |

The literature is right that the effect is stronger in small names. That is exactly why it is
untradeable there. "Go smaller where the edge is bigger" cancels itself.

### 26. Survivorship that varies across eras is a different beast
Survivorship in a dollar-neutral book measured ≈0.1 bps/day **at 30.6% uniform missing**. On a
contemporaneous symbol list missingness ramps from ~99% in old years to ~0% now (1 usable
session in 2006 vs 244 in 2025): survivorship is then confounded with era and any recent
positive cell is uninterpretable. Check coverage per year; a monotone ramp is the signature.

### 27. A placebo with stops on the range edge must mirror the geometry
With direction flipped, the opposite/mid stop landed *behind* the entry and the trade was
skipped, so the "placebo" silently kept only the trades agreeing with the signal. Mirror the
rule geometry with the direction, and compare the placebo's trade count to the real one.

### 28. A 200-seed null cannot decide a 2σ threshold
Withdrawn dollars per account are skewed (+0.9…+1.25). Three 200-seed families gave z **+1.75 /
+1.92 / +2.37** for the same real result. Use **≥ 2,000 seeds** (MC error ±0.07 in z) and report
the **percentile** too; on a skewed null the percentile rule at 97.7% is the strictest (z +2.10
passed, percentile 96.0% did not).

### 29. The null of a prop account is not $0, it is the account structure
A two-step CFD account with a static 10% floor and balance reset after each payout, payout taken
at +3% and no further risk once there: a **random-direction** book (zero edge, cost paid) withdrew
**$2,410 per account against a $540 fee**, above the fee in 99.9% of 2,000 seeds and in every
year-regime 2011-2026. On futures with a trailing drawdown the null was **below** the fee at every
size ($153-282 vs $300). Compare every prop strategy with this null, never with zero.

### 30. Position size is a bet on regime, not a free parameter
Same signal, same account: in the era with edge 0.75% risk gave $10,395 (z +4.13) and 2% gave
$4,299 (z +2.10); in the era without edge 2% was the max, tied with 1%. Small sizes let an edge
compound; large sizes cap exposure to negative drift. **Never choose size on the forward era**:
that is selection on the holdout.

---

## Measured constants worth knowing

| fact | value |
|---|---|
| Equity risk premium does not accrue intraday | SPY gross open→close −0.68 bps |
| Equities revert intraday, futures trend | ±3.76 bps/day, t ±2.63 |
| A gap reverts when it is noise, continues when it is news | −23.91 (announcement) vs +9.34 (none), same day, matched ADV |
| NQ spread | 1 tick 2010-2021, 2 ticks 2021-2026 |
| Median futures tick | 1.36 bps, only ~2× a liquid stock |
| Aggregator volume vs CME | r = 0.507, unusable for volume strategies |
| Max out-of-sample accuracy, index intraday direction | ~51% (GBM walk-forward, 65 causal features) vs 51.30% per-trade breakeven; independent MNQ study 50.0-50.9% |
| Zero-edge random direction passes futures evaluations | 21-25% simulated vs 16.8% published for real traders by one firm |
