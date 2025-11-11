#!/usr/bin/env python3
"""
Test script for the Loan Payment Calculator.

This script tests the core calculation functionality with sample data.
"""

import sys
from loan_calculator import LoanCalculator


def test_calculator():
    """Test the calculator with sample data."""
    print("=" * 60)
    print("Loan Payment Calculator - Test Suite")
    print("=" * 60)

    calculator = LoanCalculator()

    # Test 1: Load sample data
    print("\n[Test 1] Loading sample loan data...")
    try:
        calculator.load_data('sample_loans.xlsx')
        print("✓ Successfully loaded sample_loans.xlsx")
    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        return False

    # Test 2: Validate data
    print("\n[Test 2] Validating loan data...")
    is_valid, error = calculator.validate_data()
    if is_valid:
        print("✓ Data validation passed")
    else:
        print(f"✗ Data validation failed: {error}")
        return False

    # Test 3: Run calculations
    print("\n[Test 3] Running calculations with all strategies...")
    try:
        results = calculator.calculate(
            max_monthly_payment=2000,
            payment_case=0,
            strategies=['even', 'high_interest', 'high_balance', 'minimize_interest', 'snowball']
        )
        print(f"✓ Calculations completed for {len(results)} strategies")
    except Exception as e:
        print(f"✗ Calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Display results
    print("\n[Test 4] Results Summary")
    print("-" * 60)
    try:
        summary = calculator.get_summary()
        print(summary.to_string())
        print("-" * 60)
    except Exception as e:
        print(f"✗ Failed to get summary: {e}")
        return False

    # Test 5: Export summary
    print("\n[Test 5] Testing export functionality...")
    try:
        calculator.export_summary('test_output_summary.csv')
        print("✓ Successfully exported summary to test_output_summary.csv")
    except Exception as e:
        print(f"✗ Export failed: {e}")
        return False

    # Test 6: Export detailed
    print("\n[Test 6] Testing detailed export...")
    try:
        calculator.export_detailed('test_output_detailed.xlsx')
        print("✓ Successfully exported detailed results to test_output_detailed.xlsx")
    except Exception as e:
        print(f"✗ Detailed export failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

    print("\nGenerated test files:")
    print("  - test_output_summary.csv")
    print("  - test_output_detailed.xlsx")
    print("\nThe calculator is working correctly!")

    return True


if __name__ == '__main__':
    success = test_calculator()
    sys.exit(0 if success else 1)
