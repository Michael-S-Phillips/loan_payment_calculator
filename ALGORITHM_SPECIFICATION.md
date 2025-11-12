# Loan Payment Calculator - Algorithm Specification

## Core Mathematical Framework

Each month, we perform these calculations:

### 1. Interest Accrual
```
accrued_interest[i] = balance[i] × (annual_rate[i] / 12)
total_interest_this_month = sum(accrued_interest[i])
```

### 2. Principal Budget
```
principal_budget = max_monthly_payment - total_interest_this_month
```

If `principal_budget ≤ 0`, we cannot pay even the interest - this is an error state.

### 3. Minimum Principal Required
Each loan has a minimum TOTAL payment (principal + interest). The minimum principal is:
```
min_principal[i] = max(0, min_total_payment[i] - accrued_interest[i])
total_min_principal_required = sum(min_principal[i])
```

### 4. Constraint Handling (Critical!)
**Case A**: `total_min_principal_required ≤ principal_budget`
- We can meet all minimums
- Use minimums as-is
- Calculate extra available: `extra = principal_budget - total_min_principal_required`

**Case B**: `total_min_principal_required > principal_budget`
- We CANNOT meet all minimum principal requirements
- Scale all minimums proportionally: `scaled_min[i] = min_principal[i] × (principal_budget / total_min_principal_required)`
- No extra available to allocate
- **This is a key difference from MATLAB - need to understand how it handles this**

### 5. Strategy-Specific Allocation

#### Snowball Method
```
principal_payment = scaled_min.copy()
lowest_balance_idx = argmin(balance[i] for active loans)
principal_payment[lowest_balance_idx] += extra
```

**Key**: ALL extra goes to the one loan with lowest balance.

#### High Interest First
```
principal_payment = scaled_min.copy()
highest_interest_idx = argmax(balance[i] × rate[i] for active loans)
principal_payment[highest_interest_idx] += extra
```

**Key**: ALL extra goes to the one loan with highest accrued interest.

#### High Balance First
```
principal_payment = scaled_min.copy()
highest_balance_idx = argmax(balance[i] for active loans)
principal_payment[highest_balance_idx] += extra
```

**Key**: ALL extra goes to the one loan with highest principal balance.

#### Even Payments
```
principal_payment = scaled_min.copy()
per_loan_extra = extra / num_active_loans
for each active loan:
    principal_payment[i] += per_loan_extra
```

**Key**: Extra is distributed equally among all active loans.

#### Minimize Accrued Interest
```
Use linear programming to solve:
    minimize: sum((balance[i] - principal_payment[i]) × rate[i])
    subject to:
        sum(principal_payment[i]) ≤ principal_budget
        principal_payment[i] ≥ scaled_min[i]
        principal_payment[i] ≤ balance[i]
```

**Key**: This is a true optimization problem. The solution may not allocate to the "obvious" target loan.

### 6. Overpayment Handling

After allocation, some loans might receive more than their remaining balance:

```
overpayment_remainder = 0
for each loan:
    if principal_payment[i] > balance[i]:
        overpayment_remainder += principal_payment[i] - balance[i]
        principal_payment[i] = balance[i]
```

### 7. Redistribute Overpayment Remainder

The overpayment needs to go somewhere. The strategy determines where:

**Snowball**: Give to lowest remaining balance
**High Interest**: Give to highest accrued interest
**High Balance**: Give to highest balance
**Even**: Distribute equally
**Minimize**: Give to highest accrued interest (or could re-solve optimization)

Process:
```
while overpayment_remainder > 0 and active_loans_remain:
    target_idx = find_target_by_strategy(strategy, balance, rate)
    can_pay = min(overpayment_remainder, balance[target_idx])
    principal_payment[target_idx] += can_pay
    overpayment_remainder -= can_pay
    balance[target_idx] -= can_pay
    if balance[target_idx] < tolerance:
        mark_as_inactive(target_idx)
```

### 8. Update State

```
balance[i] -= principal_payment[i]
balance[i] = max(0, balance[i])  # Handle floating point errors

total_monthly_payment = total_interest_this_month + sum(principal_payment[i])
```

## Important Notes

1. **Payment tracking**: The payment_table should show ACTUAL principal paid each month, including overpayment redistribution.

2. **Monthly payment consistency**: Each month's total payment equals interest + principal. This should NOT always equal exactly max_monthly_payment:
   - If minimums can't be met, it's less
   - If we're in the last month with small balance, it's less

3. **Loan completion**: A loan is complete when balance < 0.01 (tolerance)

4. **Minimum payment semantics**:
   - Minimum payment is TOTAL (principal + interest)
   - We calculate minimum PRINCIPAL from it
   - If the minimum can't be met due to budget constraints, we scale proportionally

5. **Strategy purity**:
   - Each strategy must be internally consistent
   - Don't let constraint handling "leak" into the strategy logic
   - The strategy decides where extra goes (or how to optimize)
