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


def _enforce_minimum_payments(min_payments: np.ndarray, available_budget: float, principal_balances: np.ndarray = None) -> np.ndarray:
    """
    Enforce minimum payment constraints intelligently.

    If sum of minimum payments exceeds available budget, scale them proportionally BUT
    protect loans with substantial balances from being scaled down too far.

    Rules:
    - Loans with balance > $200: Scale minimums, but never below 50% of original
    - Loans with balance $100-$200: Scale minimums, but never below 25% of original
    - Loans with balance < $100: Can scale to near-zero (they're nearly paid off)

    Args:
        min_payments: Array of minimum monthly payment amounts
        available_budget: Total budget available for principal payments
        principal_balances: Optional array of principal balances for smart scaling

    Returns:
        Adjusted minimum payments array (respecting substantial loans' minimums)
    """
    min_payments = min_payments.copy()
    sum_min = np.sum(min_payments)

    if sum_min > available_budget:
        if principal_balances is not None:
            # First pass: establish minimum floors based on balance size
            min_floors = np.zeros_like(min_payments)

            # Loans with large balances need to maintain minimum payments
            large_balance_mask = principal_balances > 200
            min_floors[large_balance_mask] = min_payments[large_balance_mask] * 0.5  # At least 50%

            medium_balance_mask = (principal_balances > 100) & (principal_balances <= 200)
            min_floors[medium_balance_mask] = min_payments[medium_balance_mask] * 0.25  # At least 25%

            # Small balance loans can go to near-zero

            # Second pass: allocate budget respecting floors
            total_floors = np.sum(min_floors)

            if total_floors <= available_budget:
                # We can meet all the floors
                remaining_budget = available_budget - total_floors
                remaining_minimums = np.maximum(0, min_payments - min_floors)
                total_remaining = np.sum(remaining_minimums)

                if total_remaining > 0:
                    scale_factor = remaining_budget / total_remaining
                    scale_factor = min(scale_factor, 1.0)  # Don't exceed original minimums
                    min_payments = min_floors + (remaining_minimums * scale_factor)
                else:
                    min_payments = min_floors
            else:
                # Can't even meet the floors - scale them down proportionally
                scale_factor = available_budget / total_floors
                min_payments = min_floors * scale_factor
        else:
            # Fallback: proportional scaling when no balance info provided
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

        # Save starting principal before any payments
        starting_active_principal = active_principal.copy()

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

        # Compute actual principal paid (including remainder redistribution)
        actual_principal_payment = starting_active_principal - active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(actual_principal_payment)
        monthly_payments.append(float(total_payment))

        # Create payment table column
        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = actual_principal_payment
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

        # Save starting principal before any payments
        starting_active_principal = active_principal.copy()

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

        # Compute actual principal paid (including remainder redistribution)
        actual_principal_payment = starting_active_principal - active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(actual_principal_payment)
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = actual_principal_payment
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

        # Save starting principal before any payments
        starting_active_principal = active_principal.copy()

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

        # Compute actual principal paid (including remainder redistribution)
        actual_principal_payment = starting_active_principal - active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        total_payment = np.sum(accrued_interest) + np.sum(actual_principal_payment)
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        payment_col[active_idx] = actual_principal_payment
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

        # Enforce minimum principal payment constraints with intelligent scaling
        # Pass principal balances so loans with larger balances maintain their minimums
        active_min_principal_enforced = _enforce_minimum_payments(active_min_principal, mpp, active_principal)

        active_min_principal = active_min_principal_enforced

        # Find loan with lowest balance
        min_balance_idx = np.argmin(active_principal)

        # Calculate extra available after minimums
        extra_available = mpp - np.sum(active_min_principal)

        # Snowball: Send ALL extra to the lowest balance loan
        principal_payment = active_min_principal.copy()
        if extra_available > 0:
            principal_payment[min_balance_idx] += extra_available

        # Handle overpayments
        for j in range(len(principal_payment)):
            if principal_payment[j] > active_principal[j]:
                pay_remainder += principal_payment[j] - active_principal[j]
                principal_payment[j] = active_principal[j]

        # CRITICAL FIX: Save the starting principal before any modifications
        starting_active_principal = active_principal.copy()

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

        # CRITICAL FIX: Compute actual payments made (after remainder redistribution)
        # This ensures the payment_table matches the actual principal_balances
        actual_principal_payment = starting_active_principal - active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        # Use actual payments (after remainder redistribution) for totaling
        # Note: actual_principal_payment already includes remainder redistribution, so don't add extra_payment again
        total_payment = np.sum(accrued_interest) + np.sum(actual_principal_payment)
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        # Record ACTUAL payments (including remainder redistribution)
        payment_col[active_idx] = actual_principal_payment
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

        # Cap at principal balance to ensure feasibility
        active_min_principal = np.minimum(active_min_principal, active_principal)

        # Use linear programming to minimize total accrued interest for next month
        # Minimize: sum((balance - payment) * rate) = minimize -sum(payment * rate)
        # Constraints:
        #   sum(payment) <= mpp (total principal budget)
        #   payment[i] >= min_principal[i] (minimum payment constraint)
        #   payment[i] <= balance[i] (can't pay more than owed)

        num_active = len(active_principal)

        # Objective function: minimize -sum(payment * rate)
        # (negative because linprog minimizes, and we want to maximize sum(payment * rate))
        c = -active_rates*active_min_principal

        # Constraint: sum(payment) <= mpp
        A_ub = np.ones((1, num_active))
        b_ub = np.array([mpp])

        # Variable bounds: min_principal[i] <= payment[i] <= principal[i]
        bounds = [(active_min_principal[i], active_principal[i]) for i in range(num_active)]

        # Solve the optimization problem
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

        if not result.success:
            raise ValueError(f'Optimization failed: {result.message}')

        principal_payment = result.x

        # Handle overpayments
        for j in range(len(principal_payment)):
            if principal_payment[j] > active_principal[j]:
                pay_remainder += principal_payment[j] - active_principal[j]
                principal_payment[j] = active_principal[j]

        # Save starting principal before remainder redistribution
        starting_active_principal = active_principal.copy()

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

        # Compute actual payments made (including remainder redistribution)
        actual_principal_payment = starting_active_principal - active_principal

        months += 1
        interest_tally.append(float(np.sum(accrued_interest)))
        # Use actual payments (already includes remainder redistribution)
        total_payment = np.sum(accrued_interest) + np.sum(actual_principal_payment)
        monthly_payments.append(float(total_payment))

        col_name = f'Month{months}'
        payment_col = np.zeros(len(loan_numbers))
        # Record ACTUAL payments (including remainder redistribution)
        payment_col[active_idx] = actual_principal_payment
        payment_columns[col_name] = payment_col

        # Zero out very small balances to prevent floating point errors
        principal_balances[principal_balances < BALANCE_TOLERANCE] = 0
        total_balance = np.sum(principal_balances)

    payment_table = pd.DataFrame(payment_columns)
    return months, payment_table, monthly_payments, interest_tally


def milp_lifetime_optimal(
    max_monthly_payment: float,
    payment_case: int,
    loan_numbers: np.ndarray,
    interest_rates: np.ndarray,
    principal_balances: np.ndarray,
    min_monthly_payments: np.ndarray
) -> Tuple[int, pd.DataFrame, List[float], List[float]]:
    """
    Mixed Integer Linear Programming (MILP) lifetime optimizer.

    Solves a single comprehensive optimization problem that minimizes total interest
    accrued over the entire repayment horizon, with explicit balance dynamics and
    minimum payment enforcement via binary variables.

    Budget Interpretation (payment_case=0):
    - max_monthly_payment is the TOTAL monthly budget (principal + interest)
    - Interest accrues on remaining balance
    - Remaining budget after interest is available for principal reduction

    Advantages over monthly optimization:
    - Optimizes the entire payment sequence simultaneously
    - Properly models balance dynamics: bal[t] = (1+r)*bal[t-1] - payment[t]
    - Uses binary variables to enforce minimum payments only when loans are active
    - Guarantees global optimality (within solver tolerance)

    Requires: pulp, CBC solver

    Trade-off: More rigorous approach but computationally more intensive.
    """
    import pulp

    BALANCE_TOLERANCE = 0.01

    # Estimate planning horizon: use 2x the max simple payoff estimate
    max_months_estimate = int(np.sum(principal_balances) / (max_monthly_payment / len(principal_balances)) * 1.5) + 5
    T = min(max(max_months_estimate, 30), 360)  # Cap at 360 months, min 30

    N = len(principal_balances)
    monthly_rates = interest_rates.copy()  # Assume already in decimal form (monthly)

    # ========================================================================
    # Build MILP Model
    # ========================================================================

    model = pulp.LpProblem("minimize_lifetime_interest", pulp.LpMinimize)

    # Decision variables
    # bal[i, t]: balance of loan i after month t
    # pay[i, t]: payment to loan i in month t (t >= 1)
    # z[i, t]: binary indicator that loan i is active at start of month t

    bal = {}
    pay = {}
    z = {}

    for i in range(N):
        for t in range(T + 1):
            bal[(i, t)] = pulp.LpVariable(f"bal_{i}_{t}", lowBound=0, cat="Continuous")
        for t in range(1, T + 1):
            pay[(i, t)] = pulp.LpVariable(f"pay_{i}_{t}", lowBound=0, cat="Continuous")
            z[(i, t)] = pulp.LpVariable(f"z_{i}_{t}", lowBound=0, upBound=1, cat="Binary")

    # ========================================================================
    # Constraints
    # ========================================================================

    # Initial balances
    for i in range(N):
        model += bal[(i, 0)] == float(principal_balances[i])

    # Big-M constants for constraints
    M_bal = principal_balances * 5.0  # Conservative upper bound on balance
    M_pay = np.minimum(max_monthly_payment, principal_balances * 5.0)

    # Dynamics and constraints for each month
    for t in range(1, T + 1):
        # Monthly budget constraint: Total payment (interest + principal) <= budget
        # This matches payment_case=0: max_monthly_payment is the total monthly budget
        total_interest = pulp.lpSum(
            float(monthly_rates[i]) * bal[(i, t - 1)]
            for i in range(N)
        )
        total_principal = pulp.lpSum(pay[(i, t)] for i in range(N))
        model += total_interest + total_principal <= max_monthly_payment

        for i in range(N):
            r_i = float(monthly_rates[i])
            m_i = float(min_monthly_payments[i])

            # Balance update: bal[i, t] = (1 + r_i) * bal[i, t-1] - pay[i, t]
            model += bal[(i, t)] == (1.0 + r_i) * bal[(i, t-1)] - pay[(i, t)]

            # Binary activation: if bal[i, t-1] > 0 then z[i, t] must be 1
            # Enforce: bal[i, t-1] <= M_bal[i] * z[i, t]
            model += bal[(i, t - 1)] <= M_bal[i] * z[(i, t)]

            # Minimum payment enforcement: if active then pay >= m_i
            model += pay[(i, t)] >= m_i * z[(i, t)]

            # Maximum payment enforcement: if not active then pay must be 0
            model += pay[(i, t)] <= M_pay[i] * z[(i, t)]

            # No overpayment: cannot pay more than what's accrued (plus prior balance)
            model += pay[(i, t)] <= (1.0 + r_i) * bal[(i, t - 1)]

    # Final balance: all loans must be paid off within T months
    for i in range(N):
        model += bal[(i, T)] == 0

    # ========================================================================
    # Objective: Minimize total interest accrued
    # ========================================================================
    # Total interest = sum over all months of (monthly_rate[i] * balance_start_of_month[i,t])

    model += pulp.lpSum(
        float(monthly_rates[i]) * bal[(i, t - 1)]
        for i in range(N)
        for t in range(1, T + 1)
    )

    # ========================================================================
    # Solve
    # ========================================================================

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=300)
    result = model.solve(solver)

    if result != pulp.LpStatusOptimal:
        raise ValueError(f"MILP solver failed: status={pulp.LpStatus[model.status]}")

    # ========================================================================
    # Extract solution
    # ========================================================================

    # Extract payment and balance variables
    payment_array = np.zeros((T, N))
    balance_array = np.zeros((T + 1, N))

    for i in range(N):
        for t in range(T + 1):
            balance_array[t, i] = bal[(i, t)].varValue or 0.0
        for t in range(1, T + 1):
            payment_array[t - 1, i] = pay[(i, t)].varValue or 0.0

    # Find actual payoff month
    payoff_month = T
    for t in range(1, T + 1):
        if np.sum(balance_array[t]) < BALANCE_TOLERANCE:
            payoff_month = t
            break

    actual_months = payoff_month

    # Build output structures
    months_list = list(range(1, actual_months + 1))
    payment_columns = {'loanNumber': loan_numbers}
    monthly_payments_list = []
    interest_tally_list = []

    for t in months_list:
        t_idx = t - 1  # Convert to 0-indexed
        month_col = f'Month{t}'

        # Add payment column
        payment_columns[month_col] = payment_array[t_idx]

        # Calculate interest for this month (on starting balance)
        interest_this_month = np.sum(balance_array[t_idx] * monthly_rates)
        interest_tally_list.append(float(interest_this_month))

        # Total payment for this month (interest + principal)
        total_payment_this_month = interest_this_month + np.sum(payment_array[t_idx])
        monthly_payments_list.append(float(total_payment_this_month))

    payment_table = pd.DataFrame(payment_columns)

    return actual_months, payment_table, monthly_payments_list, interest_tally_list
