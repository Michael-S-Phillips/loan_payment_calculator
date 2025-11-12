# Loan Payment Calculator

A Python application for comparing different loan repayment strategies. Load your loan data, run calculations for multiple strategies, and export results to see which approach saves you the most money over the lifetime of your loans.

## Features

- **Multiple Strategies**: Compare 5 different payment allocation methods
- **Flexible Input**: Load data from Excel, CSV, TSV, or text files
- **Detailed Results**: View month-by-month payment plans and summaries
- **Export Options**: Save results to Excel or CSV format

## Quick Start

### Using Conda (Recommended)

```bash
conda env create -f environment.yml
conda activate loan-calculator
python main.py
```

### Using pip

```bash
pip install -r requirements.txt
python main.py
```

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Installation

### Requirements
- Python 3.7+
- pandas
- numpy
- openpyxl
- PySimpleGUI

### Setup with Conda

1. Install [Conda or Miniconda](https://conda.io/projects/conda/en/latest/user-guide/install/)
2. Clone or download this repository
3. Create the environment:
   ```bash
   conda env create -f environment.yml
   ```
4. Activate the environment:
   ```bash
   conda activate loan-calculator
   ```

### Setup with pip

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Launching the Application

```bash
python main.py
```

The application window will open with a professional PyQt5 interface.

### Two Ways to Input Loan Data

#### Option 1: Upload a File
1. Click the **"Upload File"** tab
2. Review the format requirements shown
3. Click **"Download Template"** to get an example Excel file
4. Click **"Browse"** to select your loan file (Excel, CSV, TSV, or Text)
5. Click **"Load File"** to import

#### Option 2: Manual Entry
1. Click the **"Manual Entry"** tab
2. Fill in loan details:
   - **Name** - Loan identifier (e.g., "Student Loan A")
   - **Principal** - Current balance
   - **Min Payment** - Minimum monthly payment required
   - **Interest Rate (%)** - Annual interest rate
3. Click **"Add Loan"** to add each loan to the table
4. Use **"Remove"** button to delete loans as needed

### Settings

- **Maximum Monthly Payment** - The total amount you can pay each month
- **Strategies** - Select which payment strategies you want to compare (all 5 are selected by default)

### Calculate

Click **"Calculate"** to run the analysis:
- A progress bar will appear during calculations
- Status bar shows "Running calculations..." with real-time feedback
- When complete, results automatically display in the summary table
- Export buttons become enabled

### Results

The results table shows for each strategy:
- **Strategy** - Name of the payment approach
- **Months** - Time (in months) to pay off all loans
- **Total Cost** - Total of all monthly payments
- **Total Interest** - Total interest paid over life of loans

### Export Results

#### Export Summary
- Quick overview with just the totals
- Saves as Excel or CSV

#### Export Detailed
- Full Excel workbook with payment tables
- Shows month-by-month breakdown for each loan
- Separate sheets for each strategy

## How It Works

1. **Load Data** - Upload a file or manually enter your loan information
2. **Set Payment** - Enter your maximum monthly payment amount
3. **Select Strategies** - Choose which repayment strategies to compare (all 5 are selected by default)
4. **Calculate** - Click Calculate to run the analysis (progress bar shows status)
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

## Payment Calculation

The calculator uses **Fixed Total Payment** mode:
- You specify your maximum monthly payment
- Formula: Total Payment = Interest Charges + Principal Reduction
- The calculator distributes available principal payments according to the selected strategy
- If a loan is paid off early, remaining funds automatically go to the next highest priority loan

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
