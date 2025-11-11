#!/usr/bin/env python
"""
Debug script to trace snowball method calculations at month 10.
"""

import numpy as np
import pandas as pd
from loan_calculator import LoanCalculator

def debug_snowball():
    """Debug the snowball method with detailed logging."""

    # Load the user's data
    input_file = "/Users/phillipsm/Documents/Professional/Loans/UpdatedNov2025/loans_info.xlsx"

    calculator = LoanCalculator()
    calculator.load_data(input_file)

    # Display the loaded loans
    print("Loaded loans:")
    df = calculator.loan_data
    # Use only first 8 loans (exclude mortgage as user mentioned)
    df = df.iloc[:8].copy()
    calculator.loan_data = df

    for idx, row in df.iterrows():
        print(f"  Loan {int(row.iloc[0])}: Balance=${row.iloc[4]:.2f}, Min Payment=${row.iloc[5]:.2f}, Rate={row.iloc[6]:.2f}%")

    print(f"\nBudget: $1000/month")
    print(f"Payment case: 0 (fixed total payment)")

    # Get the data in the format needed for the calculation
    loan_numbers = df.iloc[:, 0].values
    principal_balances = pd.to_numeric(df.iloc[:, 4]).values
    min_monthly_payments = pd.to_numeric(df.iloc[:, 5]).values
    annual_interest_rates = pd.to_numeric(df.iloc[:, 6]).values
    monthly_interest_rates = annual_interest_rates / 100 / 12

    # Run the calculation
    try:
        calculator.calculate(
            max_monthly_payment=1000.0,
            payment_case=0,
            strategies=['snowball']
        )

        results = calculator.get_strategy_results('snowball')
        months = results['months']
        payment_table = results['payment_table']
        monthly_payments = results['monthly_payments']
        interest_tally = results['interest_tally']

        print(f"\nCalculation complete: {months} months to payoff")
        print(f"\nPayment table (first 25 months):")
        cols_to_show = ['loanNumber'] + [f'Month{i}' for i in range(1, min(26, months + 1))]
        cols_available = [c for c in cols_to_show if c in payment_table.columns]
        print(payment_table[cols_available].to_string())

        # Look at month 10 specifically
        print(f"\n\n=== MONTH 10 ANALYSIS ===")
        month10_col = 'Month10'
        if month10_col in payment_table.columns:
            month10_payments = payment_table[month10_col].values
            print(f"Principal payments in Month 10:")
            for loan_idx, (loan_num, payment) in enumerate(zip(loan_numbers, month10_payments)):
                original_balance = principal_balances[loan_idx]
                # Calculate balance at start of month 10
                balance_so_far = 0
                for m in range(1, 10):
                    month_col = f'Month{m}'
                    if month_col in payment_table.columns:
                        balance_so_far += payment_table[month_col].values[loan_idx]
                current_balance = original_balance - balance_so_far
                print(f"  Loan {int(loan_num)}: Payment=${payment:.2f}, Balance before month 10=${current_balance:.2f}")

        # Check loans 1 and 7 specifically
        print(f"\n\n=== LOANS 1 AND 7 DETAIL ===")
        try:
            loan_1_idx = int(np.where(loan_numbers == 1)[0][0])
            loan_7_idx = int(np.where(loan_numbers == 7)[0][0])

            print(f"Loan 1: Min payment=${min_monthly_payments[loan_1_idx]:.2f}")
            print(f"Loan 7: Min payment=${min_monthly_payments[loan_7_idx]:.2f}")

            # Get the row indices in the payment_table DataFrame
            loan_1_row_idx = int(np.where(payment_table['loanNumber'].values == 1)[0][0])
            loan_7_row_idx = int(np.where(payment_table['loanNumber'].values == 7)[0][0])

            print(f"\nMonthly principal payments:")
            print(f"Month  |  Loan 1  |  Loan 7")
            print(f"-------|----------|--------")
            for m in range(1, min(25, months + 1)):
                month_col = f'Month{m}'
                if month_col in payment_table.columns:
                    p1 = payment_table[month_col].iloc[loan_1_row_idx]
                    p7 = payment_table[month_col].iloc[loan_7_row_idx]
                    print(f"{m:5d}  | ${p1:7.2f} | ${p7:7.2f}")
        except Exception as e:
            print(f"Error analyzing loans 1 and 7: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_snowball()
