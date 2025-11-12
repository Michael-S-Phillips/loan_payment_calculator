"""
Streamlit web interface for the Loan Payment Calculator.

Provides a user-friendly web application for comparing loan repayment strategies.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from typing import Dict, List
from loan_calculator import LoanCalculator
from plot_strategies import StrategyPlotter

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Loan Payment Calculator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
        font-weight: 600;
    }
    .result-highlight {
        padding: 10px;
        border-radius: 5px;
        background-color: #f0f2f6;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# Session State Initialization
# ============================================================================

if 'calculator' not in st.session_state:
    st.session_state.calculator = LoanCalculator()

if 'loans_data' not in st.session_state:
    st.session_state.loans_data = None

if 'results' not in st.session_state:
    st.session_state.results = None

if 'summary' not in st.session_state:
    st.session_state.summary = None

# ============================================================================
# Header
# ============================================================================

st.title("💰 Loan Payment Calculator")
st.markdown("Compare different loan repayment strategies and find the optimal payment plan for your situation.")

# ============================================================================
# Sidebar - Configuration
# ============================================================================

with st.sidebar:
    st.header("⚙️ Settings")

    # Maximum monthly payment
    max_payment = st.number_input(
        "Maximum Monthly Payment Budget",
        min_value=10.0,
        value=1000.0,
        step=50.0,
        help="The maximum total amount you can pay toward all loans per month"
    )

    # Payment case selection
    payment_case = st.radio(
        "Payment Calculation Mode",
        options=[0, 1],
        format_func=lambda x: "Fixed Total Payment" if x == 0 else "Fixed Payment After Interest",
        help="How to handle extra payments when interest requirements are low"
    )

    st.divider()

    # Strategy selection
    st.subheader("📊 Strategies")

    calc = st.session_state.calculator
    available_strategies = {key: info['name'] for key, info in calc.STRATEGIES.items()}

    selected_strategies = {}
    for key, name in available_strategies.items():
        selected_strategies[key] = st.checkbox(
            name,
            value=True,
            help=calc.STRATEGIES[key]['description']
        )

    selected_strategy_keys = [k for k, v in selected_strategies.items() if v]

    if not selected_strategy_keys:
        st.warning("Please select at least one strategy")

# ============================================================================
# Main Content - Tabs
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📥 Input", "📊 Results", "📈 Charts"])

# ============================================================================
# Tab 1: Input
# ============================================================================

with tab1:
    st.header("Loan Information")

    input_method = st.radio(
        "How would you like to enter loan data?",
        options=["Manual Entry", "Upload File"],
        horizontal=True
    )

    if input_method == "Manual Entry":
        st.subheader("Enter Your Loans")

        # Get number of loans
        num_loans = st.number_input(
            "Number of loans",
            min_value=1,
            max_value=20,
            value=3
        )

        # Loan data input
        loan_list = []

        for i in range(num_loans):
            with st.expander(f"Loan {i+1}", expanded=(i == 0)):
                col1, col2 = st.columns(2)

                with col1:
                    loan_number = st.number_input(
                        "Loan Number",
                        value=i+1,
                        key=f"loan_num_{i}"
                    )
                    lender = st.text_input(
                        "Lender/Description",
                        value=f"Loan {i+1}",
                        key=f"lender_{i}"
                    )
                    loan_type = st.selectbox(
                        "Loan Type",
                        ["Federal", "Private", "Mortgage", "Credit Card", "Other"],
                        key=f"type_{i}"
                    )
                    term = st.number_input(
                        "Term (months)",
                        value=120,
                        key=f"term_{i}"
                    )

                with col2:
                    principal = st.number_input(
                        "Principal Balance ($)",
                        min_value=0.0,
                        value=25000.0,
                        step=1000.0,
                        key=f"principal_{i}"
                    )
                    min_payment = st.number_input(
                        "Minimum Monthly Payment ($)",
                        min_value=0.0,
                        value=250.0,
                        step=50.0,
                        key=f"min_payment_{i}"
                    )
                    interest_rate = st.number_input(
                        "Annual Interest Rate (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=4.5,
                        step=0.1,
                        key=f"rate_{i}"
                    )

                loan_list.append({
                    'Loan Number': int(loan_number),
                    'Lender/Description': lender,
                    'Loan Type': loan_type,
                    'Term (months)': int(term),
                    'Principal Balance': principal,
                    'Minimum Monthly Payment': min_payment,
                    'Annual Interest Rate (%)': interest_rate
                })

        # Store loans in session state
        if loan_list:
            st.session_state.loans_data = pd.DataFrame(loan_list)

    else:  # Upload File
        st.subheader("Upload Loan Data File")

        uploaded_file = st.file_uploader(
            "Choose an Excel or CSV file",
            type=["xlsx", "xls", "csv"],
            help="File should contain columns: Loan Number, Lender/Description, Loan Type, Term (months), Principal Balance, Minimum Monthly Payment, Annual Interest Rate (%)"
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.lower().endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)

                st.session_state.loans_data = df
                st.success("File loaded successfully!")

            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

    # Display current data
    if st.session_state.loans_data is not None:
        st.subheader("📋 Current Loan Data")
        st.dataframe(st.session_state.loans_data, use_container_width=True)

        # Calculate button
        col1, col2, col3 = st.columns([1, 1, 3])

        with col1:
            if st.button("🚀 Calculate", use_container_width=True):
                if not selected_strategy_keys:
                    st.error("Please select at least one strategy")
                else:
                    try:
                        with st.spinner("Calculating... This may take a moment for MILP strategy"):
                            calc = st.session_state.calculator
                            calc.loan_data = st.session_state.loans_data

                            # Validate data
                            is_valid, error_msg = calc.validate_data()
                            if not is_valid:
                                st.error(f"Data validation error: {error_msg}")
                            else:
                                # Run calculations
                                results = calc.calculate(
                                    max_monthly_payment=max_payment,
                                    payment_case=payment_case,
                                    strategies=selected_strategy_keys
                                )

                                st.session_state.results = results
                                st.session_state.summary = calc.get_summary()

                                st.success("✅ Calculations completed!")
                                st.info("View results in the 'Results' tab")

                    except Exception as e:
                        st.error(f"Calculation error: {str(e)}")

        with col2:
            if st.session_state.loans_data is not None:
                csv_buffer = io.StringIO()
                st.session_state.loans_data.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name="loan_data.csv",
                    mime="text/csv",
                    use_container_width=True
                )

# ============================================================================
# Tab 2: Results
# ============================================================================

with tab2:
    if st.session_state.results is None:
        st.info("👈 Enter loan data and click 'Calculate' to see results")
    else:
        st.header("📊 Results Summary")

        # Display summary table
        if st.session_state.summary is not None:
            summary_df = st.session_state.summary.reset_index()

            # Format currency columns
            display_df = summary_df.copy()
            display_df['Total Cost'] = display_df['Total Cost'].apply(lambda x: f"${x:,.2f}")
            display_df['Total Interest'] = display_df['Total Interest'].apply(lambda x: f"${x:,.2f}")

            st.dataframe(display_df, use_container_width=True)

            # Highlight best strategies
            st.subheader("🏆 Strategy Comparison")

            col1, col2, col3 = st.columns(3)

            summary_orig = st.session_state.summary

            with col1:
                best_months_idx = summary_orig['Months to Payoff'].idxmin()
                best_months_strategy = summary_orig.loc[best_months_idx]
                st.metric(
                    "Fastest Payoff",
                    f"{int(best_months_strategy['Months to Payoff'])} months",
                    f"{summary_orig.loc[best_months_idx].name}"
                )

            with col2:
                best_interest_idx = summary_orig['Total Interest'].idxmin()
                best_interest_strategy = summary_orig.loc[best_interest_idx]
                st.metric(
                    "Lowest Interest",
                    f"${best_interest_strategy['Total Interest']:,.2f}",
                    f"{summary_orig.loc[best_interest_idx].name}"
                )

            with col3:
                best_cost_idx = summary_orig['Total Cost'].idxmin()
                best_cost_strategy = summary_orig.loc[best_cost_idx]
                st.metric(
                    "Lowest Total Cost",
                    f"${best_cost_strategy['Total Cost']:,.2f}",
                    f"{summary_orig.loc[best_cost_idx].name}"
                )

            st.divider()

            # Detailed results by strategy
            st.subheader("📋 Detailed Results by Strategy")

            for strategy_key, result in st.session_state.results.items():
                with st.expander(f"📄 {result['name']}", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Months to Payoff", result['months'])
                    with col2:
                        st.metric("Total Cost", f"${result['total_cost']:,.2f}")
                    with col3:
                        st.metric("Total Interest", f"${result['total_interest']:,.2f}")
                    with col4:
                        avg_payment = result['total_cost'] / result['months']
                        st.metric("Avg Monthly Payment", f"${avg_payment:,.2f}")

                    # Show payment table with total payments (principal + interest)
                    st.write("**Payment Schedule (Total Payments - Principal + Interest):**")
                    st.info("⚠️ These are the actual amounts you'll pay to each loan provider each month.")

                    try:
                        # Use the calculator's _create_payment_summary method to show total payments
                        payment_summary = st.session_state.calculator._create_payment_summary(strategy_key)

                        # Format for display
                        display_summary = payment_summary.copy()
                        month_cols = [col for col in display_summary.columns if col.startswith('Month')]
                        for col in month_cols:
                            display_summary[col] = display_summary[col].apply(
                                lambda x: f"${x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) else (x if pd.notna(x) else "")
                            )

                        st.dataframe(display_summary, use_container_width=True)

                        # Export option
                        csv_buffer = io.StringIO()
                        payment_summary.to_csv(csv_buffer, index=False)
                        st.download_button(
                            label=f"📥 Download {result['name']} Details (CSV)",
                            data=csv_buffer.getvalue(),
                            file_name=f"{result['name'].replace(' ', '_')}_details.csv",
                            mime="text/csv",
                            key=f"download_{strategy_key}"
                        )
                    except Exception as e:
                        st.error(f"Error generating payment summary: {str(e)}")
                        # Fall back to raw payment table if summary fails
                        st.write("**Raw Principal Payment Table (fallback):**")
                        payment_table = result['payment_table'].copy()
                        st.dataframe(payment_table, use_container_width=True)

# ============================================================================
# Tab 3: Charts
# ============================================================================

with tab3:
    if st.session_state.results is None:
        st.info("👈 Enter loan data and click 'Calculate' to see charts")
    else:
        st.header("📈 Strategy Comparison Charts")

        try:
            # Create comparison plots
            fig = StrategyPlotter.create_comparison_plots(st.session_state.results)
            st.pyplot(fig, use_container_width=True)

            # Download plot
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches='tight')
            buf.seek(0)

            st.download_button(
                label="📥 Download Charts (PNG)",
                data=buf.getvalue(),
                file_name="strategy_comparison.png",
                mime="image/png"
            )

        except Exception as e:
            st.error(f"Error generating charts: {str(e)}")

# ============================================================================
# Footer
# ============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9rem;'>
    <p>Loan Payment Calculator v1.0.0</p>
    <p>Compare strategies: Even • High Interest First • High Balance First • Snowball • MILP Optimal</p>
</div>
""", unsafe_allow_html=True)
