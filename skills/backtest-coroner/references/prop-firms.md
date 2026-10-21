# Prop-firm economics: the account is part of the strategy

A funded-account challenge is not "trading with someone else's money". It is a game with its own
payoff geometry, and that geometry can pay a coin flip, or rob a real edge. Price the game before
the strategy. All numbers below are from simulations on 3,605 real NQ sessions with measured cost,
validated against one firm's published pass rate.

## 1. Start from the null, not from $0
Run the strategy and a random-direction twin (same days, same cost, direction a coin flip) through
the same account program, including evaluation time and re-buying blown accounts.

- **Static floor + balance reset after payout (typical CFD two-step):** the random twin withdrew
  **$2,410 per account vs a $540 fee**, positive in 99.9% of 2,000 seeds and every year 2011-2026.
  The structure pays. Your edge is only the part *above* the null.
- **Trailing drawdown (typical futures evaluation):** the random twin sat **below** the fee at every
  size ($153-282 vs $300). Only a real edge can pay, and it has to be big.

`coroner.py prop` prints both and the z/percentile between them.

## 2. The breakeven accuracy is a function of the configuration
It is not a constant. Over 80 configurations on real paths the required directional accuracy ran
**50.96% to >58%, median 53.86%**, against a measured available ceiling of ~50.7-51%. Entry time,
stop, target, size and firm terms are all free to choose *without finding any signal*, so the
useful search is the dual: **minimise the accuracy required**, don't just maximise the accuracy
found. Quote the per-trade breakeven (e.g. 51.30%) and the account breakeven separately.

## 3. Profitable ≠ payouts
| bar | required directional accuracy |
|---|---|
| merely profitable ($/month > 0) | 50-58%, median ~56% |
| 1.00 payout / month / account | **64.58%** (1 of 16 configurations reaches it at all) |
| available (NQ, walk-forward ceiling) | ~50.7% |

The gap is not cost. It is the evaluation barrier plus payout thresholds compounding: pass, survive,
accumulate past the minimum, repeatedly. 18-54 accounts get bought per two-year program at the
ceiling, so **the evaluation barrier binds, not the payout minimum.**

## 4. Which firm rules actually cost you (each alone, policy re-optimised, p = 0.507)
| rule | payout rate | change |
|---|---|---|
| lenient reference | 1.210 / month | n/a |
| **5 winning days ≥ $150** | 0.525 | **−56.6%** |
| **trailing floor** | 0.608 | **−49.7%** (and cash flips negative) |
| **daily loss limit $1,000** | 0.634 | **−47.6%** |
| payout minimum $500 | 1.045 | −13.6% |
| consistency 40% | 1.143 | −5.5% |
| 5 trading days | 1.160 | −4.1% |
| 80% split | 1.210 | 0.0% |

Then a rule nobody had modelled killed the lenient cell: **payout frequency limits.** 1.210 with no
limit, 0.869 with one payout per 2 sessions, 0.611 weekly, 0.188 monthly. Read the payout calendar
before anything else.

## 5. Modelling traps that already happened
1. **Gaussian toy, no size cap:** EV looked positive at zero edge because as size grows the fixed
   cost vanishes and EV diverges. Real paths: 0 of 50 cells positive.
2. **Trailing floor checked at the close:** simulated zero-edge pass rate 38.6% vs the firm's
   published 16.8% for real traders. Firms ratchet the floor on the EOD balance but check the breach
   **in real time**. Fixed: 24.8%. **Never model a trailing drawdown with one draw per day**; give
   the simulator intraday excursions (`mae`, `mfe` columns).
3. Zero-edge random direction passes futures evaluations 21-25% of the time; one firm reports 16.8%
   for real traders. Real traders underperform a coin flip on that product.

## 6. Sizing and frequency
- Parameterise risk relative to the **drawdown budget**, never by contract count.
- Under a trailing drawdown, **more trades hurt**: adding a second stream dropped median income from
  $498 to $380/month and pushed big-day share to 22-102% of profit, which voids payouts under
  consistency rules. "Add uncorrelated streams" inverts under prop rules.
- Never size from in-sample expectancy: a 2.7× IS/OOS gap was the whole difference between
  "1.00%/month, viable" and "0.22%/month, EV-negative".
- Size is a bet on regime (rule 30). Do not choose it on the forward era.

## 7. Checklist before paying a fee
- [ ] Current terms verified on the firm's site today: drawdown type and when it locks, daily loss,
      min (winning) days, consistency, payout minimum, **payout frequency**, split, fee, reset price.
- [ ] Bots / EAs / copy trading allowed on **funded** accounts, not just evaluation.
- [ ] `coroner.py prop` with those terms, ≥ 2,000 seeds, with `mae`/`mfe` if the floor trails.
- [ ] Strategy beats the null at the 97.7th percentile, not just $0.
- [ ] Losing years counted, and the user knows how many there were.
