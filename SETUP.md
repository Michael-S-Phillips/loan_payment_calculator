# Setup Guide - Loan Payment Calculator

This guide explains how to set up and run the Loan Payment Calculator application using conda for package management.

## Prerequisites

- Python 3.11 or later
- Conda or Miniconda installed on your system

## Installation

### 1. Clone/Download the Repository

```bash
cd /path/to/LoanPaymentCalculator
```

### 2. Create Conda Environment

Using the provided `environment.yml` file:

```bash
conda env create -f environment.yml
```

This creates a conda environment named `loan-calculator` with all required dependencies.

### 3. Activate the Environment

```bash
conda activate loan-calculator
```

You should see `(loan-calculator)` in your terminal prompt when the environment is active.

## Running the Application

### Launch the GUI

```bash
python main.py
```

Or if you want to be explicit about which environment to use:

```bash
conda activate loan-calculator
python main.py
```

### Run Tests

To verify everything is working correctly:

```bash
python test_calculator.py
```

This will:
1. Load sample loan data from `sample_loans.xlsx`
2. Run all 5 payment strategies
3. Display a summary of results
4. Export test results to CSV and Excel files
5. Create test output files in the current directory

## Updating the Environment

If you add new dependencies to the project, you can update the `environment.yml` file and reinstall:

```bash
conda env update -f environment.yml --prune
```

The `--prune` flag removes any packages that are no longer in the file.

## Deactivating the Environment

When you're done working with the application:

```bash
conda deactivate
```

## Troubleshooting

### Conda not found
If you get "conda: command not found", you need to install Miniconda or Anaconda from: https://conda.io/projects/conda/en/latest/user-guide/install/

### Environment creation fails
Try specifying the Python version explicitly:
```bash
conda create -n loan-calculator python=3.11 pandas numpy openpyxl
conda activate loan-calculator
pip install PySimpleGUI>=4.60.0
```

### GUI doesn't display on macOS
Some systems may need additional configuration for PySimpleGUI. Try:
```bash
conda install tk
```

### Permission denied errors
If you get permission errors when running Python, try:
```bash
chmod +x main.py test_calculator.py
```

## Project Structure

```
LoanPaymentCalculator/
├── main.py                    # Application entry point
├── gui.py                     # PySimpleGUI application
├── loan_calculator.py         # Orchestrator/wrapper class
├── loan_calculator_core.py    # Core calculation algorithms
├── test_calculator.py         # Test suite
├── sample_loans.xlsx          # Sample data for testing
├── environment.yml            # Conda environment specification
├── requirements.txt           # pip requirements (alternative)
├── README.md                  # User documentation
├── SETUP.md                   # This file
└── .gitignore                 # Git ignore rules
```

## Using with pip (Alternative)

If you prefer to use pip instead of conda:

```bash
pip install -r requirements.txt
python main.py
```

However, conda is recommended as it provides better dependency management and system library handling.

## Development

### Creating a Development Environment

For development work with additional tools:

```bash
conda env create -f environment.yml
conda activate loan-calculator
conda install -c conda-forge ipython jupyter pytest black flake8
```

### Running Linting

```bash
black *.py
flake8 *.py
```

### Running Tests

```bash
pytest test_calculator.py -v
```

(Note: You'll need to install pytest first if you want full test coverage)

## Additional Resources

- [Conda Documentation](https://docs.conda.io/)
- [Python Documentation](https://docs.python.org/)
- [pandas Documentation](https://pandas.pydata.org/docs/)
- [PySimpleGUI Documentation](https://pysimplegui.readthedocs.io/)
