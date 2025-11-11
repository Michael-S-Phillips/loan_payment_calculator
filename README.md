# Loan Payment Calculator

A professional Python application for comparing different loan repayment strategies. Load your loan data, run calculations for multiple strategies, and export results to see which approach saves you the most interest.

## Features

- **Multiple Strategies**: Compare 5 different payment allocation methods
- **Intuitive GUI**: User-friendly PySimpleGUI interface
- **Flexible Input**: Load data from Excel, CSV, TSV, or text files
- **Detailed Results**: View month-by-month payment plans and summaries
- **Export Options**: Save results to Excel or CSV format

## Installation

### Requirements
- Python 3.7+
- pandas
- numpy
- openpyxl
- PySimpleGUI

### Setup

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
python main.py
```

This launches the GUI application where you can:

1. **Load Data** - Select an Excel, CSV, or TSV file with your loan information
2. **Set Parameters** - Enter your maximum monthly payment and choose payment case
3. **Select Strategies** - Choose which repayment strategies to compare
4. **Calculate** - Run the calculations
5. **Export** - Save the results as Excel or CSV files

### Input File Format

Your data file should have at least 7 columns in this order:

| Column | Description | Example |
|--------|-------------|---------|
| 0 | Loan Number | 1 |
| 1 | Lender/Description | Student Loan A |
| 2 | Loan Type | Federal |
| 3 | Term (months) | 120 |
| 4 | **Principal Balance** | 25000 |
| 5 | **Min Monthly Payment** | 250 |
| 6 | **Annual Interest Rate (%)** | 4.5 |
| 7+ | Other info (ignored) | - |

**Bold columns are required** for calculations.

### Example Data

Create a file named `loans.xlsx` or `loans.csv`:

```
Loan Number,Lender,Type,Term,Principal,Min Payment,Annual Rate
1,Student Loan A,Federal,120,25000,250,4.5
2,Student Loan B,Federal,120,15000,200,5.2
3,Credit Card,Private,60,8000,300,19.99
```

## Repayment Strategies

### 1. Even Payments
Distribute extra payment dollars equally across all loans after minimum payments.

**Best for**: Simple, straightforward approach

### 2. High Interest First
Focus extra payments on the loan with the highest interest rate.

**Best for**: Minimizing total interest paid over time

### 3. High Balance First
Focus extra payments on the loan with the largest principal balance.

**Best for**: Reducing the number of active loans faster

### 4. Minimize Accrued Interest
Optimize payment allocation to minimize total monthly interest charges.

**Best for**: Maximum flexibility in payment strategy

### 5. Snowball Method
Pay off lowest balance loans first before moving to higher balances.

**Best for**: Psychological motivation (quick wins)

## Output

### Summary Table
Shows for each strategy:
- **Months to Payoff**: Total time to eliminate all debt
- **Total Cost**: Sum of all monthly payments
- **Total Interest**: Total interest paid over the life of loans

### Detailed Payment Tables
Month-by-month breakdown of principal payments for each loan under each strategy.

## Payment Cases

### Case 0: Fixed Total Payment (default)
- You specify a fixed maximum total payment each month
- Formula: Total Payment = Interest + Principal Reduction
- The calculator determines how much extra principal to pay

### Case 1: Fixed Principal Payment
- You make the maximum payment, all interest is covered first
- Formula: Total Payment = Interest + Fixed Amount
- Useful for understanding minimum required payments

## Technical Details

The calculator uses monthly compounding interest:
- Annual rates are converted to monthly: `monthly_rate = annual_rate / 100 / 12`
- Each month's interest is calculated on remaining principal: `interest = remaining_balance × monthly_rate`

## Troubleshooting

### "Maximum monthly payment is not enough to cover accruing interest"

This means your maximum monthly payment doesn't exceed the total monthly interest charges.

**Solutions**:
- Increase your maximum monthly payment
- Use fewer loans in the analysis
- Check that interest rates are correct (should be annual %, not decimal)

### Export fails

Make sure:
- You have write permissions to the target directory
- The filename doesn't contain invalid characters
- You have openpyxl installed for Excel export: `pip install openpyxl`

## Example Workflow

1. **Launch the app**:
   ```bash
   python main.py
   ```

2. **Load your loans**:
   - Click "Browse" and select your `loans.xlsx` file
   - Click "Load File" and verify the status shows "✓ Loaded"

3. **Set parameters**:
   - Enter your maximum monthly payment: `2000`
   - Select payment case (usually Case 0 is default)

4. **Run calculations**:
   - All strategies are checked by default
   - Click "Calculate" to run

5. **View results**:
   - Compare the summary table results
   - Export if you want to keep the data

6. **Export results**:
   - Click "Export Summary" for a quick overview
   - Click "Export Detailed" for full payment tables

## Development

### Project Structure

```
LoanPaymentCalculator/
├── main.py                   # Entry point
├── gui.py                    # PySimpleGUI application
├── loan_calculator.py        # Main orchestrator class
├── loan_calculator_core.py   # Core calculation algorithms
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── .gitignore               # Git ignore rules
```

### Running Tests

The core calculation algorithms are thoroughly tested against the original MATLAB implementation.

## License

[Specify your license here]

## Support

For issues or feature requests, please open an issue or contact the maintainers.
