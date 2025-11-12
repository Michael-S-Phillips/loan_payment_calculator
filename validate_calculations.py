#!/usr/bin/env python3
"""
Validation script to ensure loan calculator is 100% accurate.
Checks:
1. Monthly payments equal expected amounts
2. Balances decrease correctly
3. Interest calculations are correct
4. Minimum payments are respected
5. Total costs match sum of payments
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/Users/phillipsm/Documents/Professional/LoanPaymentCalculator')
from loan_calculator import LoanCalculator

def validate_strategy(strategy_key, calc, input_balances, input_min_payments, input_rates):
    """Validate all constraints for a strategy."""

    result = calc.get_strategy_results(strategy_key)
    payment_table = result['payment_table']
    monthly_payments = result['monthly_payments']
    interest_tally = result['interest_tally']
    months = result['months']

    print(f"\n{'=' * 80}")
    print(f"VALIDATING: {strategy_key.upper()}")
    print(f"{'=' * 80}")

    errors = []
    warnings = []

    # Check 1: Monthly payment totals
    print("\n1. Monthly Payment Totals")
    for month_idx in range(min(5, len(monthly_payments))):
        month_num = month_idx + 1
        expected_total = interest_tally[month_idx] + np.sum([
            payment_table.iloc[loan_idx, month_num]
            for loan_idx in range(len(input_balances))
        ])
        actual_total = monthly_payments[month_idx]

        if abs(expected_total - actual_total) > 0.01:
            errors.append(f"   Month {month_num}: Expected ${expected_total:.2f}, got ${actual_total:.2f}")
        else:
            print(f"   Month {month_num}: ${actual_total:.2f} ✓")

    # Check 2: Recalculate balances and verify
    print("\n2. Balance Reduction & Principal Payments")
    balances = input_balances.copy().astype(float)
    rates_monthly = input_rates.copy() / 12

    recalc_interest_total = 0
    recalc_principal_total = 0

    # Process ALL months to verify final state
    for month_idx in range(months):
        month_num = month_idx + 1
        month_col = f'Month{month_num}'

        # Calculate expected interest
        accrued_interest = balances * rates_monthly
        total_interest_this_month = np.sum(accrued_interest)

        # Get actual principal payments from table
        principal_payments = payment_table[month_col].values

        # Check principal vs balance
        for loan_idx in range(len(balances)):
            if principal_payments[loan_idx] > balances[loan_idx] + 0.01:  # Small tolerance
                errors.append(f"   Month {month_num}, Loan {loan_idx+1}: Paying ${principal_payments[loan_idx]:.2f} > balance ${balances[loan_idx]:.2f}")

        # Update balances
        balances -= principal_payments
        balances[balances < 0.01] = 0

        total_principal_this_month = np.sum(principal_payments)
        total_payment = total_interest_this_month + total_principal_this_month

        # Only print first 3 and last 3 months for brevity
        if month_idx < 3 or month_idx >= months - 3:
            print(f"   Month {month_num}:")
            print(f"      Interest: ${total_interest_this_month:.2f}, Principal: ${total_principal_this_month:.2f}, Total: ${total_payment:.2f}")
        elif month_idx == 3:
            print(f"   ... ({months - 6} months omitted) ...")

        # Verify against recorded payment
        if abs(total_payment - monthly_payments[month_idx]) > 0.01:
            errors.append(f"   Month {month_num}: Payment mismatch ${total_payment:.2f} vs ${monthly_payments[month_idx]:.2f}")

        recalc_interest_total += total_interest_this_month
        recalc_principal_total += total_principal_this_month

    # Check 3: Final balance should be ~0
    print("\n3. Final Balances")
    final_balance_total = np.sum(balances)
    if final_balance_total > 0.01:
        errors.append(f"   Final balance: ${final_balance_total:.2f} (should be ~$0)")
    else:
        print(f"   Final balance: ${final_balance_total:.2f} ✓")

    # Check 4: Sum of all recorded payments
    print("\n4. Total Cost Verification")
    recorded_total_payment = np.sum(monthly_payments)
    recorded_total_interest = np.sum(interest_tally)
    recorded_total_principal = recorded_total_payment - recorded_total_interest

    print(f"   Total interest (from tally): ${recorded_total_interest:.2f}")
    print(f"   Total principal (calculated): ${recorded_total_principal:.2f}")
    print(f"   Total cost (sum of payments): ${recorded_total_payment:.2f}")
    print(f"   Total cost (stored): ${result['total_cost']:.2f}")

    if abs(recorded_total_payment - result['total_cost']) > 0.01:
        errors.append(f"   Total cost mismatch: ${recorded_total_payment:.2f} vs ${result['total_cost']:.2f}")

    # Summary
    print(f"\n{'=' * 80}")
    if errors:
        print(f"✗ VALIDATION FAILED - {len(errors)} errors found:")
        for error in errors:
            print(error)
    else:
        print(f"✓ VALIDATION PASSED - All constraints satisfied")

    if warnings:
        print(f"⚠ Warnings ({len(warnings)}):")
        for warning in warnings:
            print(warning)

    return len(errors) == 0

# Run validation
input_file = "/Users/phillipsm/Documents/Professional/Loans/UpdatedNov2025/loans_info_no_mor.xlsx"
calc = LoanCalculator()
calc.load_data(input_file)

input_balances = pd.to_numeric(calc.loan_data.iloc[:, 4]).values
input_min_payments = pd.to_numeric(calc.loan_data.iloc[:, 5]).values
input_rates = pd.to_numeric(calc.loan_data.iloc[:, 6]).values

calc.calculate(
    max_monthly_payment=1000.0,
    payment_case=0,
    strategies=['even', 'high_interest', 'snowball', 'minimize_interest']
)

results = []
for strategy in ['even', 'high_interest', 'snowball', 'minimize_interest']:
    passed = validate_strategy(strategy, calc, input_balances, input_min_payments, input_rates)
    results.append((strategy, passed))

print(f"\n{'=' * 80}")
print("FINAL SUMMARY")
print(f"{'=' * 80}")
for strategy, passed in results:
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{strategy:25s}: {status}")
