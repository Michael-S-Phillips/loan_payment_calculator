# Loan Payment Strategy Definitions

This document explains how each payment strategy works in the calculator.

## 1. Even Payments
**Strategy**: Distribute extra payment dollars equally across all active loans.

**Algorithm**:
1. Calculate extra available dollars: `mpp - sum(min_payments)`
2. Divide equally: `extra_per_loan = extra / num_active_loans`
3. Add to each loan's minimum payment
4. Redistribute any overpayments to loans with highest accrued interest

**Result**: Most stable/predictable payment schedule. Balanced approach.

---

## 2. High Interest First
**Strategy**: Target the loan accruing the most interest each month (rate × balance).

**Algorithm**:
1. Calculate accrued interest for each loan: `accrued = interest_rate × principal_balance`
2. Find loan with maximum accrued interest
3. Calculate equal share for all loans: `extra_dollars = extra / num_active_loans`
4. **Send ALL extra to the highest accrued interest loan**
5. Handle overpayments by redistributing to next highest accrued interest loan

**Key Point**: This targets the loan costing the most money **THIS MONTH**, not necessarily the highest rate.

**Example**: 
- Loan A: 10% rate, $100 balance → $10/month accrued
- Loan B: 5% rate, $500 balance → $25/month accrued
- **High Interest First targets Loan B** (higher monthly cost)

**Result**: Minimizes the monthly interest burden most aggressively.

---

## 3. High Balance First
**Strategy**: Target the loan with the largest principal balance.

**Algorithm**:
1. Find loan with maximum principal balance
2. Calculate equal share for all loans: `extra_dollars = extra / num_active_loans`
3. **Send ALL extra to the highest balance loan**
4. Handle overpayments by redistributing to next highest accrued interest loan

**Result**: Reduces total debt amount fastest. Psychological approach (pay off big debts).

---

## 4. Minimize Accrued Interest
**Strategy**: Solve an optimization problem to find the payment allocation that minimizes total interest accrued next month.

**Mathematical Formulation**:
```
Minimize: sum((balance_i - payment_i) × rate_i) for all i
Subject to:
  - sum(payment_i) ≤ available_budget
  - payment_i ≥ min_payment_i  (or capped at available budget if min > available)
  - payment_i ≤ balance_i
```

**Algorithm**:
1. Scale minimum payments if they exceed available budget (proportional reduction)
2. Use linear programming (scipy.optimize.linprog) to find optimal payment allocation
3. The optimizer decides how much each loan gets to minimize next month's interest

**Key Point**: This is fundamentally different from greedy approaches. It solves the optimization problem globally rather than using a greedy heuristic.

**Result**: Mathematically optimal allocation for minimizing monthly interest accrual. May produce different results than greedy strategies.

---

## 5. Snowball Method
**Strategy**: Pay off loans in order of lowest balance first (smallest to largest).

**Algorithm**:
1. Identify the active loan with the lowest principal balance
2. Send all available extra payment to that loan
3. Once paid off, move to next lowest balance loan
4. Redistribute any overpayments to next lowest balance loan

**Result**: Psychological motivation through quick wins. Pays off smaller debts first for a sense of progress.

---

## Strategy Comparison

| Strategy | Targets | Approach | Best For |
|----------|---------|----------|----------|
| Even | All equally | Proportional | Balanced approach |
| High Interest First | Monthly cost | Greedy | Minimizing monthly burden |
| High Balance First | Total debt | Greedy | Fast debt reduction |
| Minimize Accrued Interest | Optimal mix | Optimization | Mathematical optimality |
| Snowball | Lowest balance | Psychological | Motivation/quick wins |

---

## Examples

Given three loans:
- Loan A: 5% rate, $10,000 balance → $41.67/month accrued
- Loan B: 8% rate, $5,000 balance → $33.33/month accrued  
- Loan C: 3% rate, $3,000 balance → $7.50/month accrued

Available extra: $100/month (after minimums)

**Even Payments**: Each gets $33.33 extra
**High Interest First**: All $100 goes to Loan A (highest accrued interest)
**High Balance First**: All $100 goes to Loan A (highest balance)
**Minimize Accrued Interest**: Solver determines optimal split
**Snowball**: All $100 goes to Loan C (lowest balance: $3,000)

---

## Notes

- All strategies handle overpayments intelligently by redirecting excess to next highest accrued interest loan
- Floating-point tolerance (0.01) used to identify when loans are paid off
- Maximum 600 iterations (50 years) safety limit to prevent infinite loops
