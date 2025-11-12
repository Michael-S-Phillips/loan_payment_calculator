# Loan Payment Algorithm Redesign

## First Principles

Each month:
1. Calculate accrued interest on each loan: `interest[i] = balance[i] * (annual_rate[i] / 12)`
2. Calculate available principal budget: `principal_budget = max_monthly_payment - sum(interest)`
3. Allocate principal according to strategy, respecting:
   - Each loan must receive at least its minimum payment (total, not just principal)
   - No loan can receive more than its remaining balance
4. Update balances: `balance[i] -= principal_paid[i]`
5. Monthly total payment: `interest + principal` should equal `max_monthly_payment` (or less if insufficient budget)

## Key Insight from MATLAB

The MATLAB code allows monthly payments to vary and NOT always equal exactly `max_monthly_payment`. This happens when:
- Minimum payments (total) exceed the available budget
- Or when paying off loans early would overspend

This is more realistic than forcing every month to be exactly $1000.

## Strategy Algorithms (Simplified)

### 1. Even Payments
- Split principal budget equally among all active loans
- If this violates minimums, scale down proportionally
- Then add extra equally to all

### 2. High Interest First
- Pay all minimum payments
- Send all remaining principal budget to the loan with highest accrued interest (rate × balance)
- If that loan gets overpaid, redistribute remainder to next highest accrued interest

### 3. High Balance First
- Pay all minimum payments
- Send all remaining principal budget to the loan with highest principal balance
- If that loan gets overpaid, redistribute remainder to next highest principal balance

### 4. Snowball Method
- Pay all minimum payments
- Send all remaining principal budget to the loan with LOWEST principal balance
- If that loan gets overpaid, redistribute remainder to next lowest balance

### 5. Minimize Accrued Interest
- Use linear programming to find the principal payment allocation that minimizes next month's total accrued interest
- Constraints: sum(payment) ≤ principal_budget, payment[i] ≥ min_principal[i], payment[i] ≤ balance[i]
- Where min_principal[i] = max(0, min_total_payment[i] - accrued_interest[i])
- This is a TRUE optimization, not a greedy heuristic

## Implementation Notes

- All strategies need to handle the case where minimum total payments exceed the available budget
  - In this case, scale minimum payments proportionally, not just principal
- Remainder redistribution should be simple: find the target loan and pay it up to balance
- The payment_table should show ACTUAL principal paid each month
- Total monthly payment = interest + principal for that month
