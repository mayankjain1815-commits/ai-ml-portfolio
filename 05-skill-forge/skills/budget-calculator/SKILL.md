---
name: budget-calculator
description: Break income into expenses and savings, check it against the 50/30/20 rule, and flag what's off.
triggers: budget, money, income, expenses, savings, spending, salary, allowance
risk: safe
mode: action
version: 1
---

# Budget Calculator

Take a monthly income and a pile of expense categories and answer the only
question that matters: *where is the money actually going?*

## Steps

1. Inputs: `income` (monthly, required), then any number of `category=amount`
   pairs (`rent=900`, `food=300`, ...). Categories starting with `need_`,
   `want_`, or `save_` are pre-classified; everything else goes to **wants**
   by default and is labeled as such so the user can re-sort.
2. Sum expenses; compute leftover = income − expenses.
3. Compute percentages: each category's share of income, plus total
   needs / wants / savings split.
4. Compare against the **50/30/20 rule** (50% needs, 30% wants, 20% savings):
   show target amount vs actual per bucket, and the gap in currency.
5. Verdict rules:
   - negative leftover → overspending warning, name the biggest category,
   - savings < 10% of income → warn even if not negative,
   - all three buckets within ±5 points of target → "on track".

## Output format

```
INCOME      $3,000.00 / month
SPENDING
  rent        $900.00   30.0%   need
  food        $300.00   10.0%   want (default)
TOTALS      needs 40.0% | wants 30.0% | savings 15.0% | leftover $450.00
50/30/20    needs: 40.0% vs 50.0% target (-$300.00)
            ...
VERDICT     <one line>
```

## Rules

- Always show both dollars and percentages — either alone hides the story.
- Amounts are currency-agnostic: use `$` only as the default symbol.
- A leftover that is negative is an error state, not an exception: report it.
