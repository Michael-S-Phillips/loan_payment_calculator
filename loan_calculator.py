"""
Main loan payment calculator orchestrator.

Provides a high-level interface for running multiple loan repayment strategies
and comparing their results.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from loan_calculator_core import (
    evenly_distributed_payments,
    high_interest_first,
    high_balance_first,
    snowball_method,
    minimize_accrued_interest
)


class LoanCalculator:
    """Orchestrates loan payment calculations across different strategies."""

    STRATEGIES = {
        'even': {
            'name': 'Even Payments',
            'description': 'Distribute extra payments equally across all loans',
            'func': evenly_distributed_payments
        },
        'high_interest': {
            'name': 'High Interest First',
            'description': 'Focus extra payments on highest interest rate loans',
            'func': high_interest_first
        },
        'high_balance': {
            'name': 'High Balance First',
            'description': 'Focus extra payments on highest principal balance loans',
            'func': high_balance_first
        },
        'minimize_interest': {
            'name': 'Minimize Accrued Interest',
            'description': 'Optimize payment allocation to minimize monthly interest',
            'func': minimize_accrued_interest
        },
        'snowball': {
            'name': 'Snowball Method',
            'description': 'Pay off lowest balance loans first for psychological wins',
            'func': snowball_method
        }
    }

    def __init__(self):
        """Initialize the calculator."""
        self.results = {}
        self.summary = None
        self.loan_data = None

    def load_data(self, filepath: str) -> pd.DataFrame:
        """
        Load loan data from Excel, CSV, or TSV file.

        Expected columns (in order):
        0: Loan Number
        1: Lender/Description
        2: Loan Type
        3: Term (months)
        4: Principal Balance
        5: Minimum Monthly Payment
        6: Annual Interest Rate (as percentage)

        Args:
            filepath: Path to data file

        Returns:
            DataFrame with loaded loan data

        Raises:
            ValueError: If file format is not supported or data is invalid
        """
        try:
            if filepath.lower().endswith('.xlsx') or filepath.lower().endswith('.xls'):
                self.loan_data = pd.read_excel(filepath)
            elif filepath.lower().endswith('.csv'):
                self.loan_data = pd.read_csv(filepath)
            elif filepath.lower().endswith('.tsv'):
                self.loan_data = pd.read_csv(filepath, sep='\t')
            elif filepath.lower().endswith('.txt'):
                # Try to auto-detect delimiter
                self.loan_data = pd.read_csv(filepath, sep='\s+')
            else:
                raise ValueError(f"Unsupported file format: {filepath}")

            # Validate required columns
            if len(self.loan_data.columns) < 7:
                raise ValueError(
                    f"File must have at least 7 columns. Found {len(self.loan_data.columns)}."
                )

            return self.loan_data

        except Exception as e:
            raise ValueError(f"Error loading data from {filepath}: {str(e)}")

    def validate_data(self) -> Tuple[bool, str]:
        """
        Validate that loan data is properly formatted.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.loan_data is None:
            return False, "No data loaded"

        try:
            # Check for required columns
            if len(self.loan_data.columns) < 7:
                return False, f"Need at least 7 columns, have {len(self.loan_data.columns)}"

            # Check that numeric columns are present and valid
            principal = pd.to_numeric(self.loan_data.iloc[:, 4], errors='coerce')
            min_payment = pd.to_numeric(self.loan_data.iloc[:, 5], errors='coerce')
            interest_rate = pd.to_numeric(self.loan_data.iloc[:, 6], errors='coerce')

            if principal.isna().any():
                return False, "Column 5 (Principal Balance) contains invalid numbers"
            if min_payment.isna().any():
                return False, "Column 6 (Min Monthly Payment) contains invalid numbers"
            if interest_rate.isna().any():
                return False, "Column 7 (Interest Rate) contains invalid numbers"

            if (principal <= 0).any():
                return False, "Principal balances must be positive"
            if (interest_rate < 0).any() or (interest_rate > 100).any():
                return False, "Interest rates must be between 0 and 100"

            return True, ""

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def calculate(
        self,
        max_monthly_payment: float,
        payment_case: int = 0,
        strategies: Optional[List[str]] = None
    ) -> Dict:
        """
        Run loan payment calculations for specified strategies.

        Args:
            max_monthly_payment: Maximum total monthly payment available
            payment_case: 0=fixed total payment, 1=fixed payment after interest
            strategies: List of strategy keys to run. None = all strategies

        Returns:
            Dictionary with results for each strategy

        Raises:
            ValueError: If calculation fails
        """
        if self.loan_data is None:
            raise ValueError("No loan data loaded")

        is_valid, error = self.validate_data()
        if not is_valid:
            raise ValueError(f"Invalid data: {error}")

        if strategies is None:
            strategies = list(self.STRATEGIES.keys())

        # Extract loan data
        loan_numbers = self.loan_data.iloc[:, 0].values
        principal_balances = pd.to_numeric(self.loan_data.iloc[:, 4]).values
        min_monthly_payments = pd.to_numeric(self.loan_data.iloc[:, 5]).values
        annual_interest_rates = pd.to_numeric(self.loan_data.iloc[:, 6]).values

        # Convert annual to monthly interest rates
        monthly_interest_rates = annual_interest_rates / 100 / 12

        # Run selected strategies
        self.results = {}
        summary_data = []

        for strategy_key in strategies:
            if strategy_key not in self.STRATEGIES:
                raise ValueError(f"Unknown strategy: {strategy_key}")

            strategy_info = self.STRATEGIES[strategy_key]

            try:
                months, payment_table, monthly_payments, interest_tally = strategy_info['func'](
                    max_monthly_payment=max_monthly_payment,
                    payment_case=payment_case,
                    loan_numbers=loan_numbers,
                    interest_rates=monthly_interest_rates,
                    principal_balances=principal_balances.copy(),
                    min_monthly_payments=min_monthly_payments
                )

                self.results[strategy_key] = {
                    'name': strategy_info['name'],
                    'months': months,
                    'payment_table': payment_table,
                    'monthly_payments': monthly_payments,
                    'interest_tally': interest_tally,
                    'total_cost': sum(monthly_payments),
                    'total_interest': sum(interest_tally)
                }

                summary_data.append({
                    'Strategy': strategy_info['name'],
                    'Months to Payoff': months,
                    'Total Cost': sum(monthly_payments),
                    'Total Interest': sum(interest_tally)
                })

            except Exception as e:
                raise ValueError(f"Error calculating {strategy_info['name']}: {str(e)}")

        # Create summary
        self.summary = pd.DataFrame(summary_data).set_index('Strategy')

        return self.results

    def get_summary(self) -> pd.DataFrame:
        """Get summary table of all results."""
        return self.summary

    def get_strategy_results(self, strategy_key: str) -> Dict:
        """Get detailed results for a specific strategy."""
        if strategy_key not in self.results:
            raise ValueError(f"Strategy '{strategy_key}' has not been calculated")
        return self.results[strategy_key]

    def get_payment_table(self, strategy_key: str) -> pd.DataFrame:
        """Get the detailed payment table for a strategy."""
        return self.get_strategy_results(strategy_key)['payment_table']

    def get_monthly_payments(self, strategy_key: str) -> List[float]:
        """Get the monthly payment schedule for a strategy."""
        return self.get_strategy_results(strategy_key)['monthly_payments']

    def export_summary(self, filepath: str) -> None:
        """Export summary to Excel or CSV."""
        if self.summary is None:
            raise ValueError("No results to export. Run calculations first.")

        try:
            if filepath.lower().endswith('.xlsx'):
                self.summary.to_excel(filepath)
            elif filepath.lower().endswith('.csv'):
                self.summary.to_csv(filepath)
            else:
                raise ValueError("Export format must be .xlsx or .csv")
        except Exception as e:
            raise ValueError(f"Error exporting summary: {str(e)}")

    def export_detailed(self, filepath: str) -> None:
        """
        Export detailed results with payment tables for each strategy.
        """
        if not self.results:
            raise ValueError("No results to export. Run calculations first.")

        try:
            if filepath.lower().endswith('.xlsx'):
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    # Export summary
                    if self.summary is not None:
                        self.summary.to_excel(writer, sheet_name='Summary')

                    # Export details for each strategy
                    for strategy_key, result in self.results.items():
                        sheet_name = result['name'][:31]  # Excel sheet name limit
                        payment_table = result['payment_table'].copy()
                        payment_table.to_excel(writer, sheet_name=sheet_name, index=False)

            elif filepath.lower().endswith('.csv'):
                # For CSV, just export summary
                self.summary.to_csv(filepath)
            else:
                raise ValueError("Export format must be .xlsx or .csv")

        except Exception as e:
            raise ValueError(f"Error exporting detailed results: {str(e)}")
