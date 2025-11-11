"""
PySimpleGUI application for loan payment calculator.

Provides an intuitive interface for loading loan data, running calculations,
and exporting results.
"""

import PySimpleGUI as sg
import os
import sys
from loan_calculator import LoanCalculator
from pathlib import Path
import traceback


class LoanCalculatorGUI:
    """GUI application for loan payment calculator."""

    def __init__(self):
        """Initialize the GUI application."""
        # Configure PySimpleGUI theme
        sg.theme('DarkBlue3')
        sg.set_options(font=('Helvetica', 10))

        self.calculator = LoanCalculator()
        self.current_file = None
        self.calculation_results = None

    def create_window(self):
        """Create the main application window."""

        # Define the layout
        layout = [
            # Title bar
            [sg.Text('Loan Payment Calculator', font=('Helvetica', 16, 'bold'), justification='center')],
            [sg.Text('Compare different loan repayment strategies', font=('Helvetica', 10), justification='center', text_color='gray')],
            [sg.Text('_' * 80)],

            # File selection section
            [sg.Text('Step 1: Load Loan Data', font=('Helvetica', 12, 'bold'))],
            [
                sg.Text('Input File:'),
                sg.InputText(key='-FILE-', size=(40, 1), disabled=True),
                sg.FileBrowse(
                    button_text='Browse',
                    file_types=(
                        ('All Files', '*.*'),
                        ('Excel', '*.xlsx'),
                        ('Excel', '*.xls'),
                        ('CSV', '*.csv'),
                        ('TSV', '*.tsv'),
                        ('Text', '*.txt'),
                    ),
                    key='-FILE_BROWSE-'
                )
            ],
            [sg.Button('Load File', key='-LOAD-'), sg.Text('', key='-FILE_STATUS-', text_color='green')],

            [sg.Text('_' * 80)],

            # Calculation parameters section
            [sg.Text('Step 2: Set Payment Parameters', font=('Helvetica', 12, 'bold'))],
            [
                sg.Text('Maximum Monthly Payment:'),
                sg.InputText(key='-MAX_PAYMENT-', size=(15, 1), default_text='2000'),
                sg.Text('(total amount available each month)')
            ],
            [
                sg.Text('Payment Case:'),
                sg.Radio(
                    'Fixed total payment (payment covers interest + principal)',
                    'payment_case',
                    default=True,
                    key='-CASE_0-'
                )
            ],
            [
                sg.Text(''),
                sg.Radio(
                    'Fixed principal payment (total = interest + fixed amount)',
                    'payment_case',
                    key='-CASE_1-'
                )
            ],

            [sg.Text('_' * 80)],

            # Strategy selection section
            [sg.Text('Step 3: Select Strategies', font=('Helvetica', 12, 'bold'))],
            [
                sg.Checkbox('Even Payments', key='-EVEN-', default=True),
                sg.Checkbox('High Interest First', key='-HIGH_INT-', default=True)
            ],
            [
                sg.Checkbox('High Balance First', key='-HIGH_BAL-', default=True),
                sg.Checkbox('Minimize Interest', key='-MIN_INT-', default=True)
            ],
            [
                sg.Checkbox('Snowball Method', key='-SNOWBALL-', default=True)
            ],

            [sg.Text('_' * 80)],

            # Action buttons
            [
                sg.Button('Calculate', key='-CALCULATE-', size=(12, 1), button_color=('white', 'green')),
                sg.Button('Export Summary', key='-EXPORT_SUMMARY-', size=(15, 1), disabled=True),
                sg.Button('Export Detailed', key='-EXPORT_DETAILED-', size=(15, 1), disabled=True),
                sg.Button('Clear', key='-CLEAR-', size=(8, 1)),
                sg.Button('Exit', key='-EXIT-', size=(8, 1))
            ],

            [sg.Text('_' * 80)],

            # Results section
            [sg.Text('Results Summary', font=('Helvetica', 12, 'bold'), key='-RESULTS_TITLE-', visible=False)],
            [
                sg.Table(
                    values=[],
                    headings=['Strategy', 'Months', 'Total Cost', 'Total Interest'],
                    max_col_widths=[25, 10, 15, 15],
                    auto_size_columns=False,
                    num_rows=6,
                    key='-RESULTS_TABLE-',
                    visible=False,
                    row_height=20
                )
            ],

            # Status bar
            [sg.Text('Ready', key='-STATUS-', text_color='black', font=('Helvetica', 9))]
        ]

        window = sg.Window(
            'Loan Payment Calculator',
            layout,
            size=(900, 900),
            finalize=True,
            font=('Helvetica', 10)
        )

        return window

    def format_currency(self, value):
        """Format value as currency string."""
        return f"${value:,.2f}"

    def format_number(self, value):
        """Format as number with commas."""
        return f"{value:,.0f}"

    def update_status(self, message, color='black'):
        """Update status bar message."""
        self.window['-STATUS-'].update(message, text_color=color)

    def display_results(self, results):
        """Display calculation results in the results table."""
        if not results:
            sg.popup_error('No results to display')
            return

        try:
            summary = self.calculator.get_summary()

            # Prepare table data
            table_data = []
            for idx, (strategy, row) in enumerate(summary.iterrows()):
                table_data.append([
                    strategy,
                    f"{row['Months to Payoff']:.0f}",
                    self.format_currency(row['Total Cost']),
                    self.format_currency(row['Total Interest'])
                ])

            # Update table visibility and data
            self.window['-RESULTS_TITLE-'].update(visible=True)
            self.window['-RESULTS_TABLE-'].update(values=table_data, visible=True)

            self.update_status('Calculations complete!', 'green')

        except Exception as e:
            sg.popup_error(f'Error displaying results: {str(e)}')
            self.update_status(f'Error: {str(e)}', 'red')

    def run(self):
        """Run the application event loop."""
        self.window = self.create_window()

        while True:
            event, values = self.window.read()

            # Handle window close
            if event == sg.WINDOW_CLOSED or event == '-EXIT-':
                break

            # Handle file load
            if event == '-LOAD-':
                filepath = values['-FILE_BROWSE-']
                if not filepath:
                    sg.popup_error('Please select a file')
                    continue

                try:
                    self.calculator.load_data(filepath)
                    is_valid, error = self.calculator.validate_data()

                    if not is_valid:
                        sg.popup_error(f'Invalid data: {error}')
                        self.update_status(f'Error loading file: {error}', 'red')
                        continue

                    self.current_file = filepath
                    filename = os.path.basename(filepath)
                    self.window['-FILE-'].update(filename)
                    self.window['-FILE_STATUS-'].update('✓ Loaded', text_color='green')
                    self.update_status(f'Loaded: {filename}', 'green')

                except Exception as e:
                    sg.popup_error(f'Error loading file: {str(e)}')
                    self.update_status(f'Error: {str(e)}', 'red')

            # Handle calculate
            if event == '-CALCULATE-':
                if not self.current_file:
                    sg.popup_error('Please load a file first')
                    continue

                try:
                    # Get parameters
                    max_payment = float(values['-MAX_PAYMENT-'])
                    if max_payment <= 0:
                        sg.popup_error('Maximum monthly payment must be greater than 0')
                        continue

                    payment_case = 0 if values['-CASE_0-'] else 1

                    # Get selected strategies
                    strategies = []
                    if values['-EVEN-']:
                        strategies.append('even')
                    if values['-HIGH_INT-']:
                        strategies.append('high_interest')
                    if values['-HIGH_BAL-']:
                        strategies.append('high_balance')
                    if values['-MIN_INT-']:
                        strategies.append('minimize_interest')
                    if values['-SNOWBALL-']:
                        strategies.append('snowball')

                    if not strategies:
                        sg.popup_error('Please select at least one strategy')
                        continue

                    # Run calculations
                    self.update_status('Calculating... Please wait', 'blue')
                    self.window.refresh()

                    self.calculation_results = self.calculator.calculate(
                        max_monthly_payment=max_payment,
                        payment_case=payment_case,
                        strategies=strategies
                    )

                    # Display results
                    self.display_results(self.calculation_results)

                    # Enable export buttons
                    self.window['-EXPORT_SUMMARY-'].update(disabled=False)
                    self.window['-EXPORT_DETAILED-'].update(disabled=False)

                except ValueError as e:
                    sg.popup_error(f'Calculation error: {str(e)}')
                    self.update_status(f'Error: {str(e)}', 'red')
                except Exception as e:
                    sg.popup_error(f'Unexpected error: {str(e)}\n\n{traceback.format_exc()}')
                    self.update_status(f'Error: {str(e)}', 'red')

            # Handle export summary
            if event == '-EXPORT_SUMMARY-':
                if not self.calculation_results:
                    sg.popup_error('No results to export')
                    continue

                try:
                    filepath = sg.popup_get_file(
                        'Save summary as:',
                        save_as=True,
                        file_types=(('Excel', '*.xlsx'), ('CSV', '*.csv'))
                    )

                    if filepath:
                        self.calculator.export_summary(filepath)
                        sg.popup_ok(f'Summary exported to:\n{filepath}')
                        self.update_status('Summary exported successfully', 'green')

                except Exception as e:
                    sg.popup_error(f'Export error: {str(e)}')
                    self.update_status(f'Export failed: {str(e)}', 'red')

            # Handle export detailed
            if event == '-EXPORT_DETAILED-':
                if not self.calculation_results:
                    sg.popup_error('No results to export')
                    continue

                try:
                    filepath = sg.popup_get_file(
                        'Save detailed results as:',
                        save_as=True,
                        file_types=(('Excel', '*.xlsx'), ('CSV', '*.csv'))
                    )

                    if filepath:
                        self.calculator.export_detailed(filepath)
                        sg.popup_ok(f'Detailed results exported to:\n{filepath}')
                        self.update_status('Detailed results exported successfully', 'green')

                except Exception as e:
                    sg.popup_error(f'Export error: {str(e)}')
                    self.update_status(f'Export failed: {str(e)}', 'red')

            # Handle clear
            if event == '-CLEAR-':
                self.window['-FILE-'].update('')
                self.window['-FILE_STATUS-'].update('')
                self.window['-FILE_BROWSE-'].update('')
                self.window['-MAX_PAYMENT-'].update('2000')
                self.window['-CASE_0-'].update(True)
                self.window['-CASE_1-'].update(False)
                self.window['-EVEN-'].update(True)
                self.window['-HIGH_INT-'].update(True)
                self.window['-HIGH_BAL-'].update(True)
                self.window['-MIN_INT-'].update(True)
                self.window['-SNOWBALL-'].update(True)
                self.window['-RESULTS_TITLE-'].update(visible=False)
                self.window['-RESULTS_TABLE-'].update(values=[], visible=False)
                self.window['-EXPORT_SUMMARY-'].update(disabled=True)
                self.window['-EXPORT_DETAILED-'].update(disabled=True)
                self.current_file = None
                self.calculation_results = None
                self.update_status('Cleared', 'black')

        self.window.close()


def main():
    """Entry point for the application."""
    try:
        app = LoanCalculatorGUI()
        app.run()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
