"""
Plotting utilities for loan payment strategies.
Visualizes payment schedules, interest accumulation, and strategy comparison.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Dict, List


class StrategyPlotter:
    """Creates professional plots for loan payment strategies."""

    # Colors for each strategy (distinct and accessible)
    STRATEGY_COLORS = {
        'even': '#1f77b4',  # Blue
        'high_interest': '#ff7f0e',  # Orange
        'high_balance': '#2ca02c',  # Green
        'minimize_interest': '#d62728',  # Red
        'snowball': '#9467bd'  # Purple
    }

    # Markers for each strategy
    STRATEGY_MARKERS = {
        'even': 's',  # square
        'high_interest': '^',  # triangle
        'high_balance': 'o',  # circle
        'minimize_interest': '*',  # star
        'snowball': 'x'  # x
    }

    STRATEGY_NAMES = {
        'even': 'Even Payments',
        'high_interest': 'High Interest First',
        'high_balance': 'High Balance First',
        'minimize_interest': 'Minimize Accrued Interest',
        'snowball': 'Snowball Method'
    }

    @staticmethod
    def create_comparison_plots(results: Dict) -> plt.Figure:
        """
        Create comprehensive comparison plots for all strategies.

        Args:
            results: Dictionary from calculator.calculate() with results for each strategy

        Returns:
            matplotlib Figure with 4 subplots
        """
        fig = plt.figure(figsize=(16, 12))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        # Plot 1: Monthly Payment Schedule
        ax1 = fig.add_subplot(gs[0, 0])
        StrategyPlotter._plot_monthly_payments(ax1, results)

        # Plot 2: Cumulative Interest Over Time
        ax2 = fig.add_subplot(gs[0, 1])
        StrategyPlotter._plot_cumulative_interest(ax2, results)

        # Plot 3: Summary Comparison (bar chart)
        ax3 = fig.add_subplot(gs[1, 0])
        StrategyPlotter._plot_summary_comparison(ax3, results)

        # Plot 4: Monthly Interest Accrual
        ax4 = fig.add_subplot(gs[1, 1])
        StrategyPlotter._plot_monthly_interest(ax4, results)

        fig.suptitle('Loan Payment Strategy Comparison', fontsize=16, fontweight='bold')
        return fig

    @staticmethod
    def _plot_monthly_payments(ax, results: Dict):
        """Plot monthly payment schedule for each strategy."""
        for strategy_key, result in results.items():
            monthly_payments = result['monthly_payments']
            months = range(1, len(monthly_payments) + 1)

            color = StrategyPlotter.STRATEGY_COLORS.get(strategy_key, '#000000')
            marker = StrategyPlotter.STRATEGY_MARKERS.get(strategy_key, 'o')
            label = StrategyPlotter.STRATEGY_NAMES.get(strategy_key, strategy_key)

            # Plot every nth point to avoid clutter
            step = max(1, len(months) // 50)  # Show roughly 50 points max
            ax.plot(months[::step], monthly_payments[::step], color=color, marker=marker,
                    label=label, linewidth=2, markersize=6)

        ax.set_xlabel('Month', fontsize=11, fontweight='bold')
        ax.set_ylabel('Monthly Payment ($)', fontsize=11, fontweight='bold')
        ax.set_title('Monthly Payment Schedule', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc='best')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    @staticmethod
    def _plot_cumulative_interest(ax, results: Dict):
        """Plot cumulative interest paid over time for each strategy."""
        for strategy_key, result in results.items():
            interest_tally = result['interest_tally']
            cumulative_interest = np.cumsum(interest_tally)
            months = range(1, len(cumulative_interest) + 1)

            color = StrategyPlotter.STRATEGY_COLORS.get(strategy_key, '#000000')
            marker = StrategyPlotter.STRATEGY_MARKERS.get(strategy_key, 'o')
            label = StrategyPlotter.STRATEGY_NAMES.get(strategy_key, strategy_key)

            # Plot every nth point to avoid clutter
            step = max(1, len(months) // 50)
            ax.plot(months[::step], cumulative_interest[::step], color=color, marker=marker,
                    label=label, linewidth=2, markersize=6)

        ax.set_xlabel('Month', fontsize=11, fontweight='bold')
        ax.set_ylabel('Cumulative Interest Paid ($)', fontsize=11, fontweight='bold')
        ax.set_title('Cumulative Interest Over Time', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc='best')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    @staticmethod
    def _plot_summary_comparison(ax, results: Dict):
        """Create bar chart comparing key metrics."""
        strategies = []
        months_list = []
        interest_list = []

        for strategy_key, result in results.items():
            label = StrategyPlotter.STRATEGY_NAMES.get(strategy_key, strategy_key)
            strategies.append(label)
            months_list.append(result['months'])
            interest_list.append(result['total_interest'])

        # Create grouped bar chart
        x = np.arange(len(strategies))
        width = 0.35

        # Normalize months to make the bars comparable
        max_months = max(months_list)
        months_normalized = [m / max_months * max(interest_list) for m in months_list]

        bars1 = ax.bar(x - width/2, months_normalized, width, label='Months to Payoff (scaled)',
                       color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, interest_list, width, label='Total Interest Paid',
                       color='#e74c3c', alpha=0.8)

        ax.set_ylabel('Amount / Months (scaled)', fontsize=11, fontweight='bold')
        ax.set_title('Strategy Comparison: Payoff Time vs Interest', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(strategies, rotation=45, ha='right', fontsize=9)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'${height:,.0f}', ha='center', va='bottom', fontsize=8)

    @staticmethod
    def _plot_monthly_interest(ax, results: Dict):
        """Plot monthly interest accrual for each strategy."""
        for strategy_key, result in results.items():
            interest_tally = result['interest_tally']
            months = range(1, len(interest_tally) + 1)

            color = StrategyPlotter.STRATEGY_COLORS.get(strategy_key, '#000000')
            marker = StrategyPlotter.STRATEGY_MARKERS.get(strategy_key, 'o')
            label = StrategyPlotter.STRATEGY_NAMES.get(strategy_key, strategy_key)

            # Plot every nth point to avoid clutter
            step = max(1, len(months) // 50)
            ax.plot(months[::step], interest_tally[::step], color=color, marker=marker,
                    label=label, linewidth=2, markersize=6)

        ax.set_xlabel('Month', fontsize=11, fontweight='bold')
        ax.set_ylabel('Monthly Interest Accrual ($)', fontsize=11, fontweight='bold')
        ax.set_title('Monthly Interest Accrual', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc='best')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
