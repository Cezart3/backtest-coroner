# Pre-registration template

Write this file **before** any result is computed and commit it (a git timestamp is the cheapest
notary). Anything already looked at is in-sample and must be declared as such.

```markdown
# Pre-registration: <family id> <name>          date: YYYY-MM-DD

## 1. Hypothesis and mechanism
One sentence: what moves price, why it should persist, who is on the other side.
Prediction made BEFORE data: sign, rough size (bps or R), where it should be strongest.

## 2. Data
Instrument(s), source, bar size, span, time zone and session calendar, cost model and how it was
validated (rule 4), known gaps / survivorship (rule 26).
Already-seen data (in-sample by definition): ...

## 3. Cells
Exact list of variants to be computed (signal set × exit set × instrument). Count them.
Multiple-testing correction applies per signal set (rule 13).

## 4. Eras
In-sample era: YYYY-YYYY.   Holdout era(s): YYYY-YYYY (a DIFFERENT regime, rule 1).
The holdout is read once, after the in-sample verdict is frozen.

## 5. Apparatus gate (evaluated before any cell, rule 8)
- data density / coverage threshold: ...
- lookahead control that MUST fire: ...       expected: t > ...
- placebo that MUST NOT fire (varies the dimension under test, rule 7): ...
- injection probe R/S/C with planted size: ... (rule 8b)
Gate failure = NULL (fix construction blind and re-run), not FAIL.

## 6. Gates for PASS (all required)
- net expectancy > ... with t ≥ ... in-sample
- c* ≥ cost paid (rule 15)
- positive in ≥ .../... years; continuous maxDD ≤ ... (rule 11)
- holdout net > 0 and ≥ ...% of in-sample expectancy
- beats random-direction null at percentile ≥ 97.7 with ≥ 2,000 seeds (rule 28)
- (prop) beats the account null under the firm's current terms (rule 29)

## 7. Kill conditions and what is forbidden after a FAIL
FAIL closes the family. Forbidden: re-tuning parameters on the holdout, widening stops,
switching instruments to the one that worked, choosing size on the forward era (rule 30).
A new idea gets a new pre-registration.

## 8. Power statement
Smallest effect this design would detect at the gates (run the injection probe at that size).
```
