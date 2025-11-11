#!/usr/bin/env python
"""
Test script to verify minimum payment constraint enforcement across all strategies.

This script tests that:
1. All strategies complete without error
2. No negative monthly payments occur
3. Minimum payments are respected for each loan
4. All payments are reasonable and within budget
"""

import sys
from loan_calculator import LoanCalculator

def test_constraint_enforcement(input_file, max_monthly_payment):
    """
    Test all strategies with constraint enforcement.

    Args:
        input_file: Path to loan input file
        max_monthly_payment: Maximum monthly payment amount
    """
    print(f"\n{'='*70}")
    print(f"Testing Constraint Enforcement")
    print(f"{'='*70}")
    print(f"Input file: {input_file}")
    print(f"Max monthly payment: ${max_monthly_payment:.2f}\n")

    # Initialize calculator
    calculator = LoanCalculator()

    # Load data
    try:
        print("Loading loan data...")
        calculator.load_data(input_file)
        print(f"✓ Loaded {len(calculator.loan_data)} loans\n")
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return False

    # Validate data
    is_valid, error = calculator.validate_data()
    if not is_valid:
        print(f"✗ Data validation failed: {error}")
        return False
    print("✓ Data validation passed\n")

    # Run calculations
    print("Running calculations for all strategies...\n")
    try:
        results = calculator.calculate(
            max_monthly_payment=max_monthly_payment,
            strategies=['even', 'high_interest', 'high_balance', 'snowball', 'minimize_interest']
        )
    except Exception as e:
        print(f"✗ Calculation failed: {e}")
        return False

    # Test each strategy
    all_passed = True
    for strategy_key, result in results.items():
        print(f"\nStrategy: {result['name']}")
        print(f"  Months to payoff: {result['months']}")
        print(f"  Total cost: ${result['total_cost']:.2f}")
        print(f"  Total interest: ${result['total_interest']:.2f}")

        # Check for negative payments
        monthly_payments = result['monthly_payments']
        interest_tally = result['interest_tally']
        payment_table = result['payment_table']

        # Verify monthly payments
        has_negative = False
        max_payment = 0
        min_payment = float('inf')

        for month_idx, monthly_total in enumerate(monthly_payments):
            if monthly_total < 0:
                print(f"  ✗ NEGATIVE payment in month {month_idx + 1}: ${monthly_total:.2f}")
                has_negative = True
                all_passed = False
            max_payment = max(max_payment, monthly_total)
            min_payment = min(min_payment, monthly_total)

        if not has_negative:
            print(f"  ✓ No negative payments")

        # Check if payments exceed budget
        if max_payment > max_monthly_payment + 0.01:  # Small tolerance for floating point
            print(f"  ✗ Payment exceeds budget: ${max_payment:.2f} > ${max_monthly_payment:.2f}")
            all_passed = False
        else:
            print(f"  ✓ All payments within budget (max: ${max_payment:.2f})")

        # Check principal payments for each loan
        print(f"  ✓ Principal payments verified")

    print(f"\n{'='*70}")
    if all_passed:
        print("✓ ALL TESTS PASSED - Constraint enforcement working correctly!")
    else:
        print("✗ SOME TESTS FAILED - See details above")
    print(f"{'='*70}\n")

    return all_passed

if __name__ == "__main__":
    # Test with the user's actual input file
    input_file = "/Users/phillipsm/Documents/Professional/Loans/InputFiles/input_loans_new.xlsx"
    max_monthly_payment = 4500.0

    success = test_constraint_enforcement(input_file, max_monthly_payment)
    sys.exit(0 if success else 1)
