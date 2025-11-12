"""
Interactive visualizations for loan payment strategies using Plotly.

Provides engaging, interactive charts that let users explore their loan data dynamically.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class InteractiveStrategyVisualizer:
    """Creates interactive Plotly visualizations for loan payment strategies."""

    # Color scheme
    STRATEGY_COLORS = {
        'even': '#1f77b4',  # Blue
        'high_interest': '#ff7f0e',  # Orange
        'high_balance': '#2ca02c',  # Green
        'snowball': '#9467bd',  # Purple
        'milp_lifetime': '#17becf'  # Cyan
    }

    STRATEGY_NAMES = {
        'even': 'Even Payments',
        'high_interest': 'High Interest First',
        'high_balance': 'High Balance First',
        'snowball': 'Snowball Method',
        'milp_lifetime': 'MILP Lifetime Optimal'
    }

    @staticmethod
    def create_monthly_payment_comparison(results: Dict) -> go.Figure:
        """
        Create interactive line chart of monthly payments over time.

        Args:
            results: Dictionary from calculator.calculate()

        Returns:
            Plotly Figure with monthly payment comparison
        """
        fig = go.Figure()

        for strategy_key, result in results.items():
            monthly_payments = result['monthly_payments']
            months = list(range(1, len(monthly_payments) + 1))

            color = InteractiveStrategyVisualizer.STRATEGY_COLORS.get(strategy_key, '#000')
            label = InteractiveStrategyVisualizer.STRATEGY_NAMES.get(strategy_key, strategy_key)

            fig.add_trace(go.Scatter(
                x=months,
                y=monthly_payments,
                mode='lines+markers',
                name=label,
                line=dict(color=color, width=3),
                marker=dict(size=4),
                hovertemplate=f'<b>{label}</b><br>Month: %{{x}}<br>Payment: $%{{y:,.2f}}<extra></extra>'
            ))

        fig.update_layout(
            title='Monthly Payment Schedule by Strategy',
            xaxis_title='Month',
            yaxis_title='Monthly Payment ($)',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            yaxis=dict(
                tickformat='$,.0f',
            ),
            legend=dict(
                yanchor='top',
                y=0.99,
                xanchor='left',
                x=0.01
            )
        )

        return fig

    @staticmethod
    def create_cumulative_interest_chart(results: Dict) -> go.Figure:
        """
        Create interactive area chart of cumulative interest paid over time.

        Args:
            results: Dictionary from calculator.calculate()

        Returns:
            Plotly Figure with cumulative interest comparison
        """
        fig = go.Figure()

        for strategy_key, result in results.items():
            interest_tally = result['interest_tally']
            cumulative_interest = np.cumsum(interest_tally)
            months = list(range(1, len(cumulative_interest) + 1))

            color = InteractiveStrategyVisualizer.STRATEGY_COLORS.get(strategy_key, '#000')
            label = InteractiveStrategyVisualizer.STRATEGY_NAMES.get(strategy_key, strategy_key)

            fig.add_trace(go.Scatter(
                x=months,
                y=cumulative_interest,
                mode='lines',
                name=label,
                line=dict(color=color, width=3),
                fill='tozeroy',
                opacity=0.3,
                hovertemplate=f'<b>{label}</b><br>Month: %{{x}}<br>Cumulative Interest: $%{{y:,.2f}}<extra></extra>'
            ))

        fig.update_layout(
            title='Cumulative Interest Paid by Strategy',
            xaxis_title='Month',
            yaxis_title='Cumulative Interest Paid ($)',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            yaxis=dict(
                tickformat='$,.0f',
            ),
            legend=dict(
                yanchor='top',
                y=0.99,
                xanchor='left',
                x=0.01
            )
        )

        return fig

    @staticmethod
    def create_strategy_comparison_table(results: Dict) -> pd.DataFrame:
        """
        Create a comparison table of key metrics by strategy.

        Args:
            results: Dictionary from calculator.calculate()

        Returns:
            DataFrame with comparison metrics
        """
        data = []

        for strategy_key, result in results.items():
            label = InteractiveStrategyVisualizer.STRATEGY_NAMES.get(strategy_key, strategy_key)
            data.append({
                'Strategy': label,
                'Months': int(result['months']),
                'Total Interest': float(result['total_interest']),
                'Total Cost': float(result['total_cost']),
                'Avg Monthly': float(result['total_cost'] / result['months']),
                'Interest Savings vs Worst': 0  # Calculated below
            })

        df = pd.DataFrame(data)

        # Calculate interest savings vs worst strategy
        max_interest = df['Total Interest'].max()
        df['Interest Savings vs Worst'] = max_interest - df['Total Interest']

        return df

    @staticmethod
    def create_comparison_bar_chart(results: Dict) -> go.Figure:
        """
        Create interactive bar chart comparing key metrics.

        Args:
            results: Dictionary from calculator.calculate()

        Returns:
            Plotly Figure with grouped bars
        """
        df = InteractiveStrategyVisualizer.create_strategy_comparison_table(results)

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Total Interest Paid', 'Months to Payoff'),
            specs=[[{'secondary_y': False}, {'secondary_y': False}]]
        )

        colors = [
            InteractiveStrategyVisualizer.STRATEGY_COLORS.get(key, '#000')
            for key in results.keys()
        ]

        # Interest chart
        fig.add_trace(
            go.Bar(
                x=df['Strategy'],
                y=df['Total Interest'],
                name='Total Interest',
                marker_color=colors,
                text=df['Total Interest'].apply(lambda x: f'${x:,.0f}'),
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Interest: $%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        # Months chart
        fig.add_trace(
            go.Bar(
                x=df['Strategy'],
                y=df['Months'],
                name='Months to Payoff',
                marker_color=colors,
                text=df['Months'],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Months: %{y}<extra></extra>'
            ),
            row=1, col=2
        )

        fig.update_yaxes(title_text='Interest ($)', row=1, col=1, tickformat='$,.0f')
        fig.update_yaxes(title_text='Months', row=1, col=2)
        fig.update_xaxes(tickangle=-45, row=1, col=1)
        fig.update_xaxes(tickangle=-45, row=1, col=2)

        fig.update_layout(
            title='Strategy Comparison: Interest & Payoff Time',
            height=500,
            template='plotly_white',
            showlegend=False,
            hovermode='closest'
        )

        return fig

    @staticmethod
    def create_principal_remaining_chart(results: Dict, loan_data: pd.DataFrame) -> go.Figure:
        """
        Create chart showing remaining principal balance over time.

        Args:
            results: Dictionary from calculator.calculate()
            loan_data: Original loan data

        Returns:
            Plotly Figure with remaining principal by strategy
        """
        fig = go.Figure()

        # Use the first strategy as reference (they all pay off the same loans)
        first_strategy_key = list(results.keys())[0]
        first_result = results[first_strategy_key]
        payment_table = first_result['payment_table']

        # Get month columns
        month_cols = [col for col in payment_table.columns if col.startswith('Month')]
        num_months = len(month_cols)

        # Calculate remaining principal over time
        initial_principal = pd.to_numeric(loan_data.iloc[:, 4]).values.astype(float)
        remaining_principal = [initial_principal.sum()]  # Month 0

        principal_balances = initial_principal.copy()
        for month_col in month_cols:
            principal_payments = payment_table[month_col].values
            principal_balances = principal_balances - principal_payments
            principal_balances[principal_balances < 0.01] = 0
            remaining_principal.append(principal_balances.sum())

        months = list(range(0, len(remaining_principal)))

        fig.add_trace(go.Scatter(
            x=months,
            y=remaining_principal,
            mode='lines+markers',
            name='Remaining Principal',
            line=dict(color='#1f77b4', width=3),
            fill='tozeroy',
            marker=dict(size=6),
            hovertemplate='<b>Remaining Principal</b><br>Month: %{x}<br>Balance: $%{y:,.2f}<extra></extra>'
        ))

        # Add marker for payoff completion
        payoff_month = len(remaining_principal) - 1
        fig.add_trace(go.Scatter(
            x=[payoff_month],
            y=[0],
            mode='markers+text',
            marker=dict(size=15, color='#2ca02c', symbol='star'),
            text=['PAID OFF'],
            textposition='top center',
            name='Payoff Date',
            hovertemplate='<b>Fully Paid Off</b><br>Month: %{x}<extra></extra>'
        ))

        fig.update_layout(
            title='Remaining Principal Balance Over Time',
            xaxis_title='Month',
            yaxis_title='Remaining Principal ($)',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            yaxis=dict(
                tickformat='$,.0f',
            ),
            legend=dict(
                yanchor='top',
                y=0.99,
                xanchor='right',
                x=0.99
            )
        )

        return fig

    @staticmethod
    def create_savings_gauge(results: Dict) -> go.Figure:
        """
        Create gauge chart showing interest savings of best strategy vs worst.

        Args:
            results: Dictionary from calculator.calculate()

        Returns:
            Plotly Figure with gauge
        """
        df = InteractiveStrategyVisualizer.create_strategy_comparison_table(results)

        best_strategy = df.loc[df['Total Interest'].idxmin()]
        worst_strategy = df.loc[df['Total Interest'].idxmax()]
        savings = worst_strategy['Total Interest'] - best_strategy['Total Interest']
        savings_pct = (savings / worst_strategy['Total Interest']) * 100

        fig = go.Figure(go.Indicator(
            mode='gauge+number+delta',
            value=savings,
            title={'text': f"Interest Savings: {best_strategy['Strategy']}"},
            delta={'reference': worst_strategy['Total Interest']},
            gauge={
                'axis': {'range': [0, worst_strategy['Total Interest']]},
                'bar': {'color': '#2ca02c'},
                'steps': [
                    {'range': [0, worst_strategy['Total Interest'] * 0.5], 'color': '#e8f4f8'},
                    {'range': [worst_strategy['Total Interest'] * 0.5, worst_strategy['Total Interest']], 'color': '#b3d9e8'}
                ],
                'threshold': {
                    'line': {'color': 'red', 'width': 4},
                    'thickness': 0.75,
                    'value': worst_strategy['Total Interest']
                }
            },
            number={'prefix': '$', 'font': {'size': 30}},
            domain={'x': [0, 1], 'y': [0, 1]}
        ))

        fig.update_layout(
            height=400,
            font=dict(size=14)
        )

        return fig
