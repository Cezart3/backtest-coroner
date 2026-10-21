# The graveyard: case files

Real deaths from about 99 strategy families. Cite the matching case when a user's situation
looks the same. Format: what it looked like → cause of death → the number.

### 1. The opening range breakout that was a regime
**Looked like:** ORB on Nasdaq futures, t = +3.73 over four years, a real edge, pre-registered.
**Died of:** nonstationarity. The four years were 2021-2024. A frozen config on 10.5 unseen years:
expR **−0.043**, **3/11** positive years. An injection probe planted a drift at the breakout bar and
the engine read it at t +24.87, 11/11 years, so the engine was fine and the negative was real.
**Lesson:** rule 1, rule 8b.

### 2. The VWAP band strategy that worked on 13 of 13 instruments
**Looked like:** 163,296-config grid, edge on every contract tested, "universal".
**Died of:** same-bar fill artifact. Limit entry at the band, target checked against the other
extreme of the same M5 bar. **78.6%** same-bar trades; **71.7%** of those wins had the target printed
before the entry. Real M1 path: net −0.01 on NQ. The grid picked the tightest stop because it
maximised the artifact. Even the null gate passed, since permuted data has the same intrabar structure.
**Lesson:** rule 9. "Universal" is a property of the method, not of markets.

### 3. The calendar edge that inverted after publication
**Looked like:** pre-FOMC drift, a peer-reviewed effect with a date known years in advance. Zero
parameters, no lookahead possible. +20 to +29 bps on announcement days, 1994-2015.
**Died of:** publication. 2015-2026: **−9.64 / −6.25 / −8.54 / −12.12** bps on SPY / QQQ / IWM / DIA.
4/4 instruments inverted together, plus NQ futures separately.
**Lesson:** the cleanest nonstationarity proof: not cost, not lookahead, not overfitting, not
instrument luck. Literature effects have a half-life.

### 4. The scalper that wanted more trades
**Looked like:** "high frequency, short trades, so Sharpe scales with √N".
**Died of:** no signal. 245,000 trades, 16 cells; best gross **+0.0198 R at t 1.87 at ZERO cost**.
Three cells were significantly negative before cost.
**Lesson:** rule 18. Frequency amplifies an edge; it is not a source of one.

### 5. The learned sign that printed money
**Looked like:** a portfolio passing all six gates, Sharpe 3.79, 19/19 positive holdout years.
**Died of:** `sign(mean_IS) * net`: cost got flipped into profit on the cells signed −1.
**Lesson:** rules 2 and 3. It was caught because it was too good.

### 6. "If the breakout loses, the fade must win"
**Looked like:** a breakout losing at t −3 to −8 on several instruments: just trade the opposite.
**Died of:** geometry. 0/32 cells, portfolio t −9.57 to −15.23; stops hit in 82-92% of trades.
The inverse of a bad strategy has a different stop and target, so it loses differently, usually worse.
**Lesson:** a negative result does not imply a positive mirror.

### 7. The ML filter with 58.6% win rate
**Looked like:** XGBoost filter on breakout trades: WR 58.6%, +0.597 R/trade on test.
**Died of:** multi-timeframe features read unclosed higher-timeframe bars. The leak was later fixed
in the dataset, but the deployed model was never retrained. On the clean data the same model:
WR 35.1%, expR **−0.020**. The top SHAP features were exactly the leaked columns.
**Lesson:** when the most important features are higher-timeframe aggregates, audit their timestamps
first. Bit-exact reproduction of the advertised metrics from the leaky file proved provenance.

### 8. The walk-forward that passed 6/6
**Looked like:** an index ORB passing six walk-forward folds on 1.4 years.
**Died of:** two things. Clock skew (broker server GMT+2 fixed vs a fixed NY hour: in US DST months,
~60% of the file, the "opening range" formed an hour after the real open), and window luck (the
validation window was the best stretch of a 12.5-year series). Full history: **PF 0.91, expR −0.058**,
every year 2014-2020 negative.
**Lesson:** check the clock against the exchange calendar; 1.4 years cannot represent a regime.

### 9. The signal strongest where it cannot be traded
**Looked like:** insider-purchase signal, literature says stronger in small caps; measured gross
nearly doubles from large to small names.
**Died of:** cost grows faster. Net +8.99 → +4.30 → **−12.53** bps/day down the liquidity ladder.
**Lesson:** rule 25.

### 10. The stable IC
**Looked like:** cross-sectional factor with an IC identical across three eras.
**Died of:** the payoff was volatility-conditional: 2008 +66.8%, 2020 +31.0%, every calm year
negative. IC is scale-free; PnL is not.
**Lesson:** rule 19.

### 11. The diversified portfolio of nothing
**Looked like:** eight futures, correlation 0.16; four streams with mean ρ −0.05 in every era.
**Died of:** no component had an edge. Portfolio negative on both holdouts.
**Lesson:** rule 18, √k × 0 = 0.

### 12. The prop account that paid a coin flip
**Looked like:** a breakout variant on a two-step CFD challenge: **$4,299** withdrawn per account
against a $540 fee. Profitable!
**Died of (partially):** the random-direction twin withdrew **$2,410** on the same account. The edge
over structure was z +2.10, percentile 96.0%, under the 97.7% bar. Most of the "profit" was the
account geometry (static floor, balance reset after payout).
**Lesson:** rule 29. The null of a prop account is the structure, not $0.

### 13. The microstructure dream
**Looked like:** "with paid order-flow data we would see what moves price".
**Died of:** arithmetic. At daily resolution order flow is contemporaneous (t −61.51) not
predictive (t +1.76); at sub-minute horizons aggressive entry needed **105.7% / 71.0% / 59.1%**
accuracy at 1s / 10s / 60s (impossible / implausible / above any measured ceiling), and passive
quoting earned 0.6595 pts while adverse selection took back 0.6219 (94.3%).
**Lesson:** rule 22. Paying for data buys a latency race.

### 14. The cost model that was 29× too expensive
**Looked like:** a careful spread estimator from the literature (Corwin-Schultz).
**Died of:** never validated: it overstated the measured NQ spread **29.2×**, worse in volatile
regimes. Every verdict gated on it would have been wrong.
**Lesson:** rule 4. Validate the cost model before it becomes a gate.
