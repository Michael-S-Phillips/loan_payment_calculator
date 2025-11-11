"""
Core loan payment calculation module.

This module implements 5 different loan payment strategies:
1. Evenly Distributed - distribute extra payments equally across all loans
2. High Interest First - focus extra payments on highest interest rate loans
3. High Balance First - focus extra payments on highest principal balance loans
4. Minimize Accrued Interest - optimize to minimize total monthly interest
5. Snowball Method - pay off lowest balance loans first

All functions return:
- months: number of months to payoff
- payment_table: DataFrame with principal payments by loan and month
- monthly_payments: list of total monthly payments
- interest_tally: list of monthly interest accrual
"""

import numpy as np
import pandas as pd
from typing import Tuple, List


def evenly_distributed_payments(
    max_monthly_payment: float,
    payment_case: int,
    loan_numbers: np.ndarray,
    interest_rates: np.ndarray,
    principal_balances: np.ndarray,
    min_monthly_payments: np.ndarray
) -> Tuple[int, pd.DataFrame, List[float], List[float]]:
    """
    Payment strategy: Distribute extra payment dollars equally across all loans.

    Args:
        max_monthly_payment: Maximum total monthly payment available
        payment_case: 0=fixed total payment, 1=fixed payment after interest
        loan_numbers: Array of loan identifiers
        interest_rates: Monthly interest rates (already divided by 12)
        principal_balances: Current principal balance for each loan
        min_monthly_payments: Minimum required monthly payment per loan

    Returns:
        Tuple of (months, payment_table, monthly_payments, interest_tally)
    """
    BALANCE_TOLERANCE = 0.01  # Consider balances < $0.01 as paid off
    MAX_ITERATIONS = 600  # Safety limit (50 years at monthly payments)
    LOG_FILE = '/tmp/loan_calc_strategy_debug.log'

    months = 0
    principal_balances = principal_balances.copy().astype(float)
    interest_rates = interest_rates.copy().astype(float)
    min_monthly_payments = min_monthly_payments.copy().astype(float)
    loan_numbers = loan_numbers.copy()

    with open(LOG_FILE, 'a') as f:
        f.write(f"[evenly_distributed_payments] Starting with total balance: ${np.sum(principal_balances):.2f}\n")
        f.write(f"[evenly_distributed_payments] Max payment: ${max_monthly_payment}\n")

    # Zero out balances below tolerance
    principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
    total_balance = np.sum(principal_balances)
    interest_tally = []
    monthly_payments = []
    payment_columns = {'loanNumber': loan_numbers}

    while total_balance > BALANCE_TOLERANCE:
        # Safety check to prevent infinite loops
        if months >= MAX_ITERATIONS:
            with open(LOG_FILE, 'a') as f:
                f.write(f"[evenly_distributed_payments] ERROR: Max iterations reached at month {months}\n")
            raise ValueError(
                f'Calculation exceeded maximum iterations ({MAX_ITERATIONS} months). '
                'This may indicate an issue with your loan data or payment configuration.'
            )

        # Log progress every 100 months
        if months % 100 == 0:
            with open(LOG_FILE, 'a') as f:
                f.write(f"[evenly_distributed_payments] Month {months}: balance = ${total_balance:.2f}\n")

        # Filter for loans with remaining balance
        active_idx = principal_balances > BALANCE_TOLERANCE
        active_principal = principal_balances[active_idx]
        active_rates = interest_rates[active_idx]
        active_min_payments = min_monthly_payments[active_idx]

        pay_remainder = 0

        # Calculate accrued interest
        accrued_interest = active_rates * active_principal

        # Determine principal payment available
        if payment_case == 0:
            # Fixed total monthly payment
            mpp = max_monthly_payment - np.sum(accrued_interest)
            if mpp <= 0:
                raise ValueError(
                    'Maximum monthly payment is not enough to cover accruing interest. '
                    'Increase max_monthly_payment or reduce number of loans.'
                )
        elif payment_case == 1:
            # Fixed payment after interest (interest + principal = max_monthly_payment)
            mpp = max_monthly_payment
        else:
            raise ValueError('payment_case must be 0 or 1')

        # Distribute extra payment equally
        num_active = np.sum(active_idx)
        extra_dollars = np.ones(num_active) * (mpp - np.sum(active_min_payments)) / num_active
        principal_payment = active_min_payments + extra_dollars

        # Handle overpayments
        for j in range(len(principal_payment)):
            if principal_payment[j] > active_principal[j]:
                pay_remainder += principal_payment[j] - active_principal[j]
                principal_payment[j] = active_principal[j]

        # Update balances
        active_principal -= principal_payment
        principal_balances[active_idx] = active_principal

        # Redistribute remainder to highest interest loan
        sigma_b = np.sum(active_principal)
        extra_payment = 0

        if pay_remainder > 0 and sigma_b > 0:
            while pay_remainder > 0 and sigma_b > 0:
                accrued_interest_next = active_rates * active_principal
                remainder_idx = np.argmax(accrued_interest_next)

                if active_principal[remainder_idx] - pay_remainder < 0:
                    extra_payment += active_principal[remainder_idx]
                    pay_remainder -= active_principal[remainder_idx]
                    active_principal[remainder_idx] = 0
                else:
                    active_principal[remainder_idx] -= pay_remainder
                    extra_payment += pay_remainder
                    pay_remainder = 0

                sigma_b = np.sum(active_principal)
                principal_balances[active_idx] = active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(principal_payment) + extra_payment
        monthly_payments.append(float(total_payment))

        # Create payment table column
        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = principal_payment
        payment_columns[col_name] = payment_col

        # Zero out very small balances to prevent floating point errors
        principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
        total_balance = np.sum(principal_balances)

    with open(LOG_FILE, 'a') as f:
        f.write(f"[evenly_distributed_payments] Calculation complete: {months} months, final balance = ${total_balance:.2f}\n")
    payment_table = pd.DataFrame(payment_columns)
    return months, payment_table, monthly_payments, interest_tally


def high_interest_first(
    max_monthly_payment: float,
    payment_case: int,
    loan_numbers: np.ndarray,
    interest_rates: np.ndarray,
    principal_balances: np.ndarray,
    min_monthly_payments: np.ndarray
) -> Tuple[int, pd.DataFrame, List[float], List[float]]:
    """
    Payment strategy: Focus extra payments on the loan with highest interest rate.
    """
    BALANCE_TOLERANCE = 0.01
    MAX_ITERATIONS = 600

    months = 0
    principal_balances = principal_balances.copy().astype(float)
    interest_rates = interest_rates.copy().astype(float)
    min_monthly_payments = min_monthly_payments.copy().astype(float)
    loan_numbers = loan_numbers.copy()

    principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
    total_balance = np.sum(principal_balances)
    interest_tally = []
    monthly_payments = []
    payment_columns = {'loanNumber': loan_numbers}

    while total_balance > BALANCE_TOLERANCE:
        if months >= MAX_ITERATIONS:
            raise ValueError(
                f'Calculation exceeded maximum iterations ({MAX_ITERATIONS} months). '
                'This may indicate an issue with your loan data or payment configuration.'
            )

        active_idx = principal_balances > BALANCE_TOLERANCE
        active_principal = principal_balances[active_idx]
        active_rates = interest_rates[active_idx]
        active_min_payments = min_monthly_payments[active_idx]

        pay_remainder = 0

        accrued_interest = active_rates * active_principal

        if payment_case == 0:
            mpp = max_monthly_payment - np.sum(accrued_interest)
            if mpp <= 0:
                raise ValueError(
                    'Maximum monthly payment is not enough to cover accruing interest. '
                    'Increase max_monthly_payment or reduce number of loans.'
                )
        elif payment_case == 1:
            mpp = max_monthly_payment
        else:
            raise ValueError('payment_case must be 0 or 1')

        # Find loan with highest interest rate
        max_interest_idx = np.argmax(accrued_interest)

        # Distribute extra to highest interest loan
        num_active = np.sum(active_idx)
        extra_dollars = np.ones(num_active) * (mpp - np.sum(active_min_payments)) / num_active
        principal_payment = active_min_payments.copy()
        principal_payment[max_interest_idx] += np.sum(extra_dollars)

        # Handle overpayments
        for j in range(len(principal_payment)):
            if principal_payment[j] > active_principal[j]:
                pay_remainder += principal_payment[j] - active_principal[j]
                principal_payment[j] = active_principal[j]

        active_principal -= principal_payment
        principal_balances[active_idx] = active_principal

        # Redistribute remainder
        sigma_b = np.sum(active_principal)
        extra_payment = 0

        if pay_remainder > 0 and sigma_b > 0:
            while pay_remainder > 0 and sigma_b > 0:
                accrued_interest_next = active_rates * active_principal
                remainder_idx = np.argmax(accrued_interest_next)

                if active_principal[remainder_idx] - pay_remainder < 0:
                    extra_payment += active_principal[remainder_idx]
                    pay_remainder -= active_principal[remainder_idx]
                    active_principal[remainder_idx] = 0
                else:
                    active_principal[remainder_idx] -= pay_remainder
                    extra_payment += pay_remainder
                    pay_remainder = 0

                sigma_b = np.sum(active_principal)
                principal_balances[active_idx] = active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(principal_payment) + extra_payment
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = principal_payment
        payment_columns[col_name] = payment_col

        # Zero out very small balances to prevent floating point errors
        principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
        total_balance = np.sum(principal_balances)

    payment_table = pd.DataFrame(payment_columns)
    return months, payment_table, monthly_payments, interest_tally


def high_balance_first(
    max_monthly_payment: float,
    payment_case: int,
    loan_numbers: np.ndarray,
    interest_rates: np.ndarray,
    principal_balances: np.ndarray,
    min_monthly_payments: np.ndarray
) -> Tuple[int, pd.DataFrame, List[float], List[float]]:
    """
    Payment strategy: Focus extra payments on the loan with highest principal balance.
    """
    BALANCE_TOLERANCE = 0.01
    MAX_ITERATIONS = 600

    months = 0
    principal_balances = principal_balances.copy().astype(float)
    interest_rates = interest_rates.copy().astype(float)
    min_monthly_payments = min_monthly_payments.copy().astype(float)
    loan_numbers = loan_numbers.copy()

    principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
    total_balance = np.sum(principal_balances)
    interest_tally = []
    monthly_payments = []
    payment_columns = {'loanNumber': loan_numbers}

    while total_balance > BALANCE_TOLERANCE:
        if months >= MAX_ITERATIONS:
            raise ValueError(
                f'Calculation exceeded maximum iterations ({MAX_ITERATIONS} months). '
                'This may indicate an issue with your loan data or payment configuration.'
            )

        active_idx = principal_balances > BALANCE_TOLERANCE
        active_principal = principal_balances[active_idx]
        active_rates = interest_rates[active_idx]
        active_min_payments = min_monthly_payments[active_idx]

        pay_remainder = 0

        accrued_interest = active_rates * active_principal

        if payment_case == 0:
            mpp = max_monthly_payment - np.sum(accrued_interest)
            if mpp <= 0:
                raise ValueError(
                    'Maximum monthly payment is not enough to cover accruing interest. '
                    'Increase max_monthly_payment or reduce number of loans.'
                )
        elif payment_case == 1:
            mpp = max_monthly_payment
        else:
            raise ValueError('payment_case must be 0 or 1')

        # Find loan with highest balance
        max_balance_idx = np.argmax(active_principal)

        # Distribute extra to highest balance loan
        num_active = np.sum(active_idx)
        extra_dollars = np.ones(num_active) * (mpp - np.sum(active_min_payments)) / num_active
        principal_payment = active_min_payments.copy()
        principal_payment[max_balance_idx] += np.sum(extra_dollars)

        # Handle overpayments
        for j in range(len(principal_payment)):
            if principal_payment[j] > active_principal[j]:
                pay_remainder += principal_payment[j] - active_principal[j]
                principal_payment[j] = active_principal[j]

        active_principal -= principal_payment
        principal_balances[active_idx] = active_principal

        # Redistribute remainder
        sigma_b = np.sum(active_principal)
        extra_payment = 0

        if pay_remainder > 0 and sigma_b > 0:
            while pay_remainder > 0 and sigma_b > 0:
                remaining_principal = active_principal.copy()
                max_balance_idx = np.argmax(remaining_principal)

                if active_principal[max_balance_idx] - pay_remainder < 0:
                    extra_payment += active_principal[max_balance_idx]
                    pay_remainder -= active_principal[max_balance_idx]
                    active_principal[max_balance_idx] = 0
                else:
                    active_principal[max_balance_idx] -= pay_remainder
                    extra_payment += pay_remainder
                    pay_remainder = 0

                sigma_b = np.sum(active_principal)
                principal_balances[active_idx] = active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(principal_payment) + extra_payment
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = principal_payment
        payment_columns[col_name] = payment_col

        # Zero out very small balances to prevent floating point errors
        principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
        total_balance = np.sum(principal_balances)

    payment_table = pd.DataFrame(payment_columns)
    return months, payment_table, monthly_payments, interest_tally


def snowball_method(
    max_monthly_payment: float,
    payment_case: int,
    loan_numbers: np.ndarray,
    interest_rates: np.ndarray,
    principal_balances: np.ndarray,
    min_monthly_payments: np.ndarray
) -> Tuple[int, pd.DataFrame, List[float], List[float]]:
    """
    Payment strategy: Pay off lowest balance loans first (snowball method).
    """
    BALANCE_TOLERANCE = 0.01
    MAX_ITERATIONS = 600
    LOG_FILE = '/tmp/loan_calc_strategy_debug.log'

    months = 0
    principal_balances = principal_balances.copy().astype(float)
    interest_rates = interest_rates.copy().astype(float)
    min_monthly_payments = min_monthly_payments.copy().astype(float)
    loan_numbers = loan_numbers.copy()

    with open(LOG_FILE, 'a') as f:
        f.write(f"[snowball_method] Starting with total balance: ${np.sum(principal_balances):.2f}\n")
        f.write(f"[snowball_method] Max payment: ${max_monthly_payment}\n")

    principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
    total_balance = np.sum(principal_balances)
    interest_tally = []
    monthly_payments = []
    payment_columns = {'loanNumber': loan_numbers}

    with open(LOG_FILE, 'a') as f:
        f.write(f"[snowball_method] Entering main loop\n")

    while total_balance > BALANCE_TOLERANCE:
        if months >= MAX_ITERATIONS:
            with open(LOG_FILE, 'a') as f:
                f.write(f"[snowball_method] ERROR: Max iterations reached at month {months}\n")
            raise ValueError(
                f'Calculation exceeded maximum iterations ({MAX_ITERATIONS} months). '
                'This may indicate an issue with your loan data or payment configuration.'
            )

        # Log progress every 100 months
        if months % 100 == 0:
            with open(LOG_FILE, 'a') as f:
                f.write(f"[snowball_method] Month {months}: balance = ${total_balance:.2f}\n")

        active_idx = principal_balances > BALANCE_TOLERANCE
        active_principal = principal_balances[active_idx]
        active_rates = interest_rates[active_idx]
        active_min_payments = min_monthly_payments[active_idx]

        pay_remainder = 0

        accrued_interest = active_rates * active_principal

        if payment_case == 0:
            mpp = max_monthly_payment - np.sum(accrued_interest)
            if mpp <= 0:
                raise ValueError(
                    'Maximum monthly payment is not enough to cover accruing interest. '
                    'Increase max_monthly_payment or reduce number of loans.'
                )
        elif payment_case == 1:
            mpp = max_monthly_payment
        else:
            raise ValueError('payment_case must be 0 or 1')

        # Find loan with lowest balance
        min_balance_idx = np.argmin(active_principal)

        # Distribute extra to lowest balance loan
        num_active = np.sum(active_idx)
        extra_dollars = np.ones(num_active) * (mpp - np.sum(active_min_payments)) / num_active
        principal_payment = active_min_payments.copy()
        principal_payment[min_balance_idx] += np.sum(extra_dollars)

        # Handle overpayments
        for j in range(len(principal_payment)):
            if principal_payment[j] > active_principal[j]:
                pay_remainder += principal_payment[j] - active_principal[j]
                principal_payment[j] = active_principal[j]

        active_principal -= principal_payment
        principal_balances[active_idx] = active_principal

        # Redistribute remainder
        sigma_b = np.sum(active_principal)
        extra_payment = 0

        if pay_remainder > 0 and sigma_b > 0:
            while pay_remainder > 0 and sigma_b > 0:
                remaining_principal = active_principal.copy()
                # Find index of minimum balance among positive balances
                positive_mask = remaining_principal > 0
                if np.any(positive_mask):
                    # Get indices of positive balances and find which has minimum value
                    positive_indices = np.where(positive_mask)[0]
                    min_idx_in_positive = np.argmin(remaining_principal[positive_indices])
                    min_balance_idx = positive_indices[min_idx_in_positive]
                else:
                    # All balances are zero or negative, shouldn't happen but use argmin as fallback
                    min_balance_idx = np.argmin(remaining_principal)

                if active_principal[min_balance_idx] - pay_remainder < 0:
                    extra_payment += active_principal[min_balance_idx]
                    pay_remainder -= active_principal[min_balance_idx]
                    active_principal[min_balance_idx] = 0
                else:
                    active_principal[min_balance_idx] -= pay_remainder
                    extra_payment += pay_remainder
                    pay_remainder = 0

                sigma_b = np.sum(active_principal)
                principal_balances[active_idx] = active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(principal_payment) + extra_payment
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = principal_payment
        payment_columns[col_name] = payment_col

        # Zero out very small balances to prevent floating point errors
        principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
        total_balance = np.sum(principal_balances)

    payment_table = pd.DataFrame(payment_columns)
    return months, payment_table, monthly_payments, interest_tally


def minimize_accrued_interest(
    max_monthly_payment: float,
    payment_case: int,
    loan_numbers: np.ndarray,
    interest_rates: np.ndarray,
    principal_balances: np.ndarray,
    min_monthly_payments: np.ndarray
) -> Tuple[int, pd.DataFrame, List[float], List[float]]:
    """
    Payment strategy: Optimize payment allocation to minimize total monthly interest.
    Uses a greedy approach - pay extra toward the loan that will accrue the most interest.
    """
    BALANCE_TOLERANCE = 0.01
    MAX_ITERATIONS = 600

    months = 0
    principal_balances = principal_balances.copy().astype(float)
    interest_rates = interest_rates.copy().astype(float)
    min_monthly_payments = min_monthly_payments.copy().astype(float)
    loan_numbers = loan_numbers.copy()

    principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
    total_balance = np.sum(principal_balances)
    interest_tally = []
    monthly_payments = []
    payment_columns = {'loanNumber': loan_numbers}

    while total_balance > BALANCE_TOLERANCE:
        if months >= MAX_ITERATIONS:
            raise ValueError(
                f'Calculation exceeded maximum iterations ({MAX_ITERATIONS} months). '
                'This may indicate an issue with your loan data or payment configuration.'
            )

        active_idx = principal_balances > BALANCE_TOLERANCE
        active_principal = principal_balances[active_idx]
        active_rates = interest_rates[active_idx]
        active_min_payments = min_monthly_payments[active_idx]

        pay_remainder = 0

        accrued_interest = active_rates * active_principal

        if payment_case == 0:
            mpp = max_monthly_payment - np.sum(accrued_interest)
            if mpp <= 0:
                raise ValueError(
                    'Maximum monthly payment is not enough to cover accruing interest. '
                    'Increase max_monthly_payment or reduce number of loans.'
                )
        elif payment_case == 1:
            mpp = max_monthly_payment
        else:
            raise ValueError('payment_case must be 0 or 1')

        # Simple greedy approach: target loan with highest accrued interest
        max_interest_idx = np.argmax(accrued_interest)

        num_active = np.sum(active_idx)
        extra_dollars = np.ones(num_active) * (mpp - np.sum(active_min_payments)) / num_active
        principal_payment = active_min_payments.copy()
        principal_payment[max_interest_idx] += np.sum(extra_dollars)

        # Handle overpayments
        for j in range(len(principal_payment)):
            if principal_payment[j] > active_principal[j]:
                pay_remainder += principal_payment[j] - active_principal[j]
                principal_payment[j] = active_principal[j]

        active_principal -= principal_payment
        principal_balances[active_idx] = active_principal

        # Redistribute remainder
        sigma_b = np.sum(active_principal)
        extra_payment = 0

        if pay_remainder > 0 and sigma_b > 0:
            while pay_remainder > 0 and sigma_b > 0:
                accrued_interest_next = active_rates * active_principal
                remainder_idx = np.argmax(accrued_interest_next)

                if active_principal[remainder_idx] - pay_remainder < 0:
                    extra_payment += active_principal[remainder_idx]
                    pay_remainder -= active_principal[remainder_idx]
                    active_principal[remainder_idx] = 0
                else:
                    active_principal[remainder_idx] -= pay_remainder
                    extra_payment += pay_remainder
                    pay_remainder = 0

                sigma_b = np.sum(active_principal)
                principal_balances[active_idx] = active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(principal_payment) + extra_payment
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = principal_payment
        payment_columns[col_name] = payment_col

        # Zero out very small balances to prevent floating point errors
        principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
        total_balance = np.sum(principal_balances)

    payment_table = pd.DataFrame(payment_columns)
    return months, payment_table, monthly_payments, interest_tally
