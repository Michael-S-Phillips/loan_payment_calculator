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


def _enforce_minimum_payments(min_payments: np.ndarray, available_budget: float) -> np.ndarray:
    """
    Enforce minimum payment constraints.

    If sum of minimum payments exceeds available budget, scale them down proportionally
    to ensure all minimum payments can be made while staying within budget.

    Args:
        min_payments: Array of minimum monthly payment amounts
        available_budget: Total budget available for principal payments

    Returns:
        Adjusted minimum payments array (may be scaled down if sum exceeded budget)
    """
    min_payments = min_payments.copy()
    sum_min = np.sum(min_payments)

    if sum_min > available_budget:
        # Scale all minimum payments proportionally to fit budget
        scale_factor = available_budget / sum_min
        min_payments = min_payments * scale_factor

    return min_payments


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

    months = 0
    principal_balances = principal_balances.copy().astype(float)
    interest_rates = interest_rates.copy().astype(float)
    min_monthly_payments = min_monthly_payments.copy().astype(float)
    loan_numbers = loan_numbers.copy()

    # Zero out balances below tolerance
    principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
    total_balance = np.sum(principal_balances)
    interest_tally = []
    monthly_payments = []
    payment_columns = {'loanNumber': loan_numbers}

    while total_balance > BALANCE_TOLERANCE:
        # Safety check to prevent infinite loops
        if months >= MAX_ITERATIONS:
            raise ValueError(
                f'Calculation exceeded maximum iterations ({MAX_ITERATIONS} months). '
                'This may indicate an issue with your loan data or payment configuration.'
            )

        # Filter for loans with remaining balance
        active_idx = principal_balances > BALANCE_TOLERANCE
        active_principal = principal_balances[active_idx]
        active_rates = interest_rates[active_idx]
        active_min_payments = min_monthly_payments[active_idx].copy()

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

        # CRITICAL: Convert minimum TOTAL payments to minimum PRINCIPAL payments
        # active_min_payments are total payments, but we need to enforce the principal portion
        # If a loan requires $25 total payment and has $8 interest, minimum principal = $17
        active_min_principal = np.maximum(0, active_min_payments - accrued_interest)

        # Enforce minimum principal payment constraints
        # Note: We do NOT cap this at principal_balance. If minimum principal > balance,
        # the overpayment handler will manage it and redistribute the excess.
        active_min_principal = _enforce_minimum_payments(active_min_principal, mpp)

        # Distribute extra payment equally
        num_active = np.sum(active_idx)
        extra_available = mpp - np.sum(active_min_principal)
        if extra_available > 0:
            extra_dollars = np.ones(num_active) * extra_available / num_active
        else:
            extra_dollars = np.zeros(num_active)
        principal_payment = active_min_principal + extra_dollars

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
    Payment strategy: Focus extra payments on the loan with highest accrued interest.
    Accrued interest = interest_rate * principal_balance.
    This minimizes total interest paid over the life of all loans (ish).
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

        # CRITICAL: Convert minimum TOTAL payments to minimum PRINCIPAL payments
        active_min_principal = np.maximum(0, active_min_payments - accrued_interest)

        # Enforce minimum principal payment constraints
        # Note: We do NOT cap this at principal_balance. If minimum principal > balance,
        # the overpayment handler will manage it and redistribute the excess.
        active_min_principal = _enforce_minimum_payments(active_min_principal, mpp)

        # Find loan with highest accrued interest (rate * balance)
        max_interest_idx = np.argmax(accrued_interest)

        # Distribute extra as equal share, but give all of it to max accrued interest loan
        num_active = np.sum(active_idx)
        extra_available = mpp - np.sum(active_min_principal)
        if extra_available > 0:
            extra_dollars = np.ones(num_active) * extra_available / num_active
        else:
            extra_dollars = np.zeros(num_active)
        principal_payment = active_min_principal.copy()
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

        # CRITICAL: Convert minimum TOTAL payments to minimum PRINCIPAL payments
        active_min_principal = np.maximum(0, active_min_payments - accrued_interest)

        # Enforce minimum principal payment constraints
        # Note: We do NOT cap this at principal_balance. If minimum principal > balance,
        # the overpayment handler will manage it and redistribute the excess.
        active_min_principal = _enforce_minimum_payments(active_min_principal, mpp)

        # Find loan with highest balance
        max_balance_idx = np.argmax(active_principal)

        # Distribute extra to highest balance loan
        num_active = np.sum(active_idx)
        extra_available = mpp - np.sum(active_min_principal)
        if extra_available > 0:
            extra_dollars = np.ones(num_active) * extra_available / num_active
        else:
            extra_dollars = np.zeros(num_active)
        principal_payment = active_min_principal.copy()
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

        # CRITICAL: Convert minimum TOTAL payments to minimum PRINCIPAL payments
        active_min_principal = np.maximum(0, active_min_payments - accrued_interest)

        # Enforce minimum principal payment constraints
        active_min_principal = _enforce_minimum_payments(active_min_principal, mpp)

        # Find loan with lowest balance
        min_balance_idx = np.argmin(active_principal)

        # Distribute extra to lowest balance loan
        num_active = np.sum(active_idx)
        extra_available = mpp - np.sum(active_min_principal)
        if extra_available > 0:
            extra_dollars = np.ones(num_active) * extra_available / num_active
        else:
            extra_dollars = np.zeros(num_active)
        principal_payment = active_min_principal.copy()
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
    Payment strategy: Minimize total accrued interest for the next month.
    Uses optimization to find the payment allocation that minimizes
    sum((principal_balance - payment) * interest_rate) subject to constraints.
    """
    from scipy.optimize import linprog

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
        active_min_payments = min_monthly_payments[active_idx].copy()

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

        # CRITICAL: Convert minimum TOTAL payments to minimum PRINCIPAL payments
        # active_min_payments are total payments, but we need to enforce the principal portion
        active_min_principal = np.maximum(0, active_min_payments - accrued_interest)

        # For linear programming, we need to cap at principal balance to ensure feasibility
        active_min_principal = np.minimum(active_min_principal, active_principal)

        # Enforce minimum principal payment constraints
        active_min_principal = _enforce_minimum_payments(active_min_principal, mpp)

        # Use optimization to minimize total accrued interest for next month
        # Minimize: sum((balance - payment) * rate)
        # Which is equivalent to: maximize sum(payment * rate) since balance is constant
        # Constraints: sum(payment) <= mpp, payment >= min_payment, payment <= balance

        num_active = len(active_principal)

        # Objective: minimize sum((active_principal - payment) * active_rates)
        # = minimize sum(active_principal * active_rates) - sum(payment * active_rates)
        # The constant doesn't matter, so minimize -sum(payment * active_rates)
        # Which is maximize sum(payment * active_rates)
        c = -active_rates  # Negative because linprog minimizes

        # Constraint 1: sum(payment) <= mpp
        A_ub = np.ones((1, num_active))
        b_ub = np.array([mpp])

        # Bounds: payment[i] >= min_principal[i] and payment[i] <= principal[i]
        bounds = [(active_min_principal[i], active_principal[i]) for i in range(num_active)]

        # Solve
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

        if not result.success:
            raise ValueError(f'Optimization failed: {result.message}')

        principal_payment = result.x

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
