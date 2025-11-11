"""
PyQt5 application for loan payment calculator.

Provides a professional interface for loading loan data, running calculations,
and exporting results.
"""

import sys
import os
from pathlib import Path
import traceback
from typing import Optional, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QCheckBox, QTabWidget, QSpinBox, QDoubleSpinBox,
    QMessageBox, QStatusBar, QProgressBar, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QColor

from loan_calculator import LoanCalculator


class CalculationWorker(QObject):
    """Worker for running calculations in background thread."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    results = pyqtSignal(dict)

    def __init__(self, calculator, max_payment, strategies):
        super().__init__()
        self.calculator = calculator
        self.max_payment = max_payment
        self.strategies = strategies

    def run(self):
        """Run the calculation."""
        try:
            self.progress.emit('Starting calculations...')
            results = self.calculator.calculate(
                max_monthly_payment=self.max_payment,
                payment_case=0,  # Fixed total payment
                strategies=self.strategies
            )
            self.results.emit(results)
            self.progress.emit('Calculations complete!')
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


class LoanCalculatorApp(QMainWindow):
    """Main application window for Loan Payment Calculator."""

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.calculator = LoanCalculator()
        self.current_file = None
        self.calculation_results = None
        self.calculation_thread = None
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Loan Payment Calculator')
        self.setGeometry(100, 100, 1200, 1000)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Title
        title = QLabel('Loan Payment Calculator')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        subtitle = QLabel('Compare different loan repayment strategies')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('color: gray; font-size: 10px;')
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(10)

        # Create tabs for file upload vs manual entry
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Upload File
        self.create_file_upload_tab()

        # Tab 2: Manual Entry
        self.create_manual_entry_tab()

        main_layout.addSpacing(10)

        # Settings section
        settings_title = QLabel('Settings')
        settings_title_font = QFont()
        settings_title_font.setPointSize(12)
        settings_title_font.setBold(True)
        settings_title.setFont(settings_title_font)
        main_layout.addWidget(settings_title)

        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel('Maximum Monthly Payment:'))
        self.max_payment = QDoubleSpinBox()
        self.max_payment.setValue(2000)
        self.max_payment.setMinimum(0)
        self.max_payment.setMaximum(999999)
        settings_layout.addWidget(self.max_payment)
        settings_layout.addStretch()
        main_layout.addLayout(settings_layout)

        main_layout.addSpacing(10)

        # Strategies section
        strategies_title = QLabel('Select Strategies to Compare')
        strategies_title.setFont(settings_title_font)
        main_layout.addWidget(strategies_title)

        strategy_layout = QVBoxLayout()
        self.strategy_checks = {}
        strategies = [
            ('even', 'Even Payments - Distribute extra payments equally across all loans'),
            ('high_interest', 'High Interest First - Focus on highest interest rate loans'),
            ('high_balance', 'High Balance First - Focus on highest principal balance loans'),
            ('minimize_interest', 'Minimize Interest - Optimize to minimize monthly interest charges'),
            ('snowball', 'Snowball Method - Pay off lowest balance loans first')
        ]

        for key, label in strategies:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            self.strategy_checks[key] = checkbox
            strategy_layout.addWidget(checkbox)

        main_layout.addLayout(strategy_layout)
        main_layout.addSpacing(10)

        # Action buttons
        button_layout = QHBoxLayout()
        self.calculate_btn = QPushButton('Calculate')
        self.calculate_btn.clicked.connect(self.calculate)
        self.calculate_btn.setStyleSheet('background-color: green; color: white; font-weight: bold; padding: 5px;')
        button_layout.addWidget(self.calculate_btn)

        self.export_summary_btn = QPushButton('Export Summary')
        self.export_summary_btn.clicked.connect(self.export_summary)
        self.export_summary_btn.setEnabled(False)
        button_layout.addWidget(self.export_summary_btn)

        self.export_detailed_btn = QPushButton('Export Detailed')
        self.export_detailed_btn.clicked.connect(self.export_detailed)
        self.export_detailed_btn.setEnabled(False)
        button_layout.addWidget(self.export_detailed_btn)

        self.clear_btn = QPushButton('Clear')
        self.clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_btn)

        self.exit_btn = QPushButton('Exit')
        self.exit_btn.clicked.connect(self.close)
        button_layout.addWidget(self.exit_btn)

        main_layout.addLayout(button_layout)
        main_layout.addSpacing(10)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        main_layout.addWidget(self.progress_bar)

        # Results section
        results_title = QLabel('Results Summary')
        results_title.setFont(settings_title_font)
        results_title.setVisible(False)
        self.results_title = results_title
        main_layout.addWidget(results_title)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(['Strategy', 'Months', 'Total Cost', 'Total Interest'])
        self.results_table.setRowCount(0)
        self.results_table.setVisible(False)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.results_table)

        main_layout.addStretch()

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')

    def create_file_upload_tab(self):
        """Create the file upload tab."""
        tab = QWidget()
        layout = QVBoxLayout()

        # Guidance
        guidance = QLabel(
            'Upload a file with your loan information.\n\n'
            'Required columns (in order):\n'
            '1. Loan Number\n'
            '2. Lender/Description\n'
            '3. Loan Type\n'
            '4. Term (months)\n'
            '5. Principal Balance (REQUIRED)\n'
            '6. Minimum Monthly Payment (REQUIRED)\n'
            '7. Annual Interest Rate % (REQUIRED)\n\n'
            'Supported formats: Excel (.xlsx, .xls), CSV, TSV, Text files\n'
            'Click "Download Template" below for an example file.'
        )
        guidance.setStyleSheet('border: 1px solid #cccccc; padding: 10px; background-color: #f0f0f0;')
        layout.addWidget(guidance)

        layout.addSpacing(10)

        # Template button
        template_btn = QPushButton('Download Template File')
        template_btn.clicked.connect(self.download_template)
        layout.addWidget(template_btn)

        layout.addSpacing(10)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel('Input File:'))
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        file_layout.addWidget(self.file_input)
        self.browse_btn = QPushButton('Browse')
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)

        load_layout = QHBoxLayout()
        self.load_btn = QPushButton('Load File')
        self.load_btn.clicked.connect(self.load_file)
        load_layout.addWidget(self.load_btn)
        self.file_status = QLabel('')
        self.file_status.setStyleSheet('color: green;')
        load_layout.addWidget(self.file_status)
        load_layout.addStretch()
        layout.addLayout(load_layout)

        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, 'Upload File')

    def create_manual_entry_tab(self):
        """Create the manual loan entry tab."""
        tab = QWidget()
        layout = QVBoxLayout()

        guidance = QLabel(
            'Manually enter your loan information below.\n'
            'Fill in all fields and click "Add Loan" to add each loan.'
        )
        guidance.setStyleSheet('border: 1px solid #cccccc; padding: 10px; background-color: #f0f0f0;')
        layout.addWidget(guidance)

        layout.addSpacing(10)

        # Input fields
        input_layout = QHBoxLayout()

        input_layout.addWidget(QLabel('Name:'))
        self.loan_name_input = QLineEdit()
        self.loan_name_input.setPlaceholderText('e.g., Student Loan A')
        input_layout.addWidget(self.loan_name_input)

        input_layout.addWidget(QLabel('Principal:'))
        self.principal_input = QDoubleSpinBox()
        self.principal_input.setMaximum(999999999)
        input_layout.addWidget(self.principal_input)

        input_layout.addWidget(QLabel('Min Payment:'))
        self.min_payment_input = QDoubleSpinBox()
        self.min_payment_input.setMaximum(999999)
        input_layout.addWidget(self.min_payment_input)

        input_layout.addWidget(QLabel('Interest Rate (%):'))
        self.interest_rate_input = QDoubleSpinBox()
        self.interest_rate_input.setMaximum(100)
        self.interest_rate_input.setDecimals(2)
        input_layout.addWidget(self.interest_rate_input)

        self.add_loan_btn = QPushButton('Add Loan')
        self.add_loan_btn.clicked.connect(self.add_loan)
        input_layout.addWidget(self.add_loan_btn)

        layout.addLayout(input_layout)

        layout.addSpacing(10)

        # Loans table
        self.manual_loans_table = QTableWidget()
        self.manual_loans_table.setColumnCount(5)
        self.manual_loans_table.setHorizontalHeaderLabels(['Name', 'Principal', 'Min Payment', 'Interest Rate (%)', 'Remove'])
        self.manual_loans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.manual_loans_table)

        layout.addSpacing(10)

        # Status label
        self.manual_status = QLabel('No loans added yet')
        self.manual_status.setStyleSheet('color: #666666; font-style: italic;')
        layout.addWidget(self.manual_status)

        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, 'Manual Entry')

    def download_template(self):
        """Download template file."""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, 'Save Template File', 'loan_template.xlsx', 'Excel Files (*.xlsx)'
            )
            if filepath:
                self.calculator.create_template_file(filepath)
                QMessageBox.information(self, 'Success', f'Template file created:\n{filepath}')
                self.statusBar.showMessage('Template file downloaded')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error creating template: {str(e)}')

    def browse_file(self):
        """Browse for a loan data file."""
        file_filter = 'All Files (*);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;TSV Files (*.tsv);;Text Files (*.txt)'
        filepath, _ = QFileDialog.getOpenFileName(self, 'Load Loan Data', '', file_filter)
        if filepath:
            self.file_input.setText(filepath)

    def load_file(self):
        """Load the selected file."""
        filepath = self.file_input.text()
        if not filepath:
            QMessageBox.warning(self, 'Warning', 'Please select a file')
            return

        try:
            self.calculator.load_data(filepath)
            is_valid, error = self.calculator.validate_data()

            if not is_valid:
                QMessageBox.critical(self, 'Invalid Data', f'Error: {error}')
                self.statusBar.showMessage(f'Error: {error}')
                return

            self.current_file = filepath
            filename = Path(filepath).name
            self.file_status.setText('✓ Loaded')
            self.statusBar.showMessage(f'Loaded: {filename}')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error loading file: {str(e)}')
            self.statusBar.showMessage(f'Error: {str(e)}')

    def add_loan(self):
        """Add a loan from manual entry."""
        try:
            name = self.loan_name_input.text().strip()
            principal = self.principal_input.value()
            min_payment = self.min_payment_input.value()
            interest_rate = self.interest_rate_input.value()

            if not name:
                QMessageBox.warning(self, 'Warning', 'Please enter a loan name')
                return
            if principal <= 0:
                QMessageBox.warning(self, 'Warning', 'Principal must be greater than 0')
                return
            if min_payment < 0:
                QMessageBox.warning(self, 'Warning', 'Minimum payment cannot be negative')
                return
            if interest_rate < 0 or interest_rate > 100:
                QMessageBox.warning(self, 'Warning', 'Interest rate must be between 0 and 100')
                return

            # Add to table
            row = self.manual_loans_table.rowCount()
            self.manual_loans_table.insertRow(row)

            self.manual_loans_table.setItem(row, 0, QTableWidgetItem(name))

            principal_item = QTableWidgetItem(f'${principal:,.2f}')
            principal_item.setFlags(principal_item.flags() & ~Qt.ItemIsEditable)
            self.manual_loans_table.setItem(row, 1, principal_item)

            payment_item = QTableWidgetItem(f'${min_payment:,.2f}')
            payment_item.setFlags(payment_item.flags() & ~Qt.ItemIsEditable)
            self.manual_loans_table.setItem(row, 2, payment_item)

            rate_item = QTableWidgetItem(f'{interest_rate:.2f}%')
            rate_item.setFlags(rate_item.flags() & ~Qt.ItemIsEditable)
            self.manual_loans_table.setItem(row, 3, rate_item)

            # Remove button
            remove_btn = QPushButton('Remove')
            remove_btn.clicked.connect(lambda: self.remove_loan(row))
            self.manual_loans_table.setCellWidget(row, 4, remove_btn)

            # Clear inputs
            self.loan_name_input.clear()
            self.principal_input.setValue(0)
            self.min_payment_input.setValue(0)
            self.interest_rate_input.setValue(0)

            # Update status
            self.manual_status.setText(f'{self.manual_loans_table.rowCount()} loan(s) added')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error adding loan: {str(e)}')

    def remove_loan(self, row):
        """Remove a loan from the table."""
        self.manual_loans_table.removeRow(row)
        self.manual_status.setText(f'{self.manual_loans_table.rowCount()} loan(s) added')

    def get_loan_data(self):
        """Get loan data from manual entry or file."""
        if self.tabs.currentIndex() == 0:
            # File upload tab
            if not self.current_file:
                QMessageBox.warning(self, 'Warning', 'Please load a file first')
                return None
            return self.calculator.loan_data
        else:
            # Manual entry tab
            if self.manual_loans_table.rowCount() == 0:
                QMessageBox.warning(self, 'Warning', 'Please add at least one loan')
                return None

            # Create DataFrame from manual entry
            import pandas as pd
            import numpy as np

            loans = []
            for row in range(self.manual_loans_table.rowCount()):
                name = self.manual_loans_table.item(row, 0).text()
                principal = float(self.manual_loans_table.item(row, 1).text().replace('$', '').replace(',', ''))
                min_payment = float(self.manual_loans_table.item(row, 2).text().replace('$', '').replace(',', ''))
                interest = float(self.manual_loans_table.item(row, 3).text().replace('%', ''))

                loans.append({
                    'Loan Number': row + 1,
                    'Description': name,
                    'Loan Type': 'Manual',
                    'Term': 0,
                    'Principal': principal,
                    'Min Payment': min_payment,
                    'Interest Rate': interest
                })

            data = pd.DataFrame(loans)
            self.calculator.loan_data = data
            return data

    def calculate(self):
        """Run the calculations."""
        try:
            # Get loan data
            loan_data = self.get_loan_data()
            if loan_data is None:
                return

            # Validate
            is_valid, error = self.calculator.validate_data()
            if not is_valid:
                QMessageBox.critical(self, 'Invalid Data', f'Error: {error}')
                return

            # Get parameters
            max_payment = float(self.max_payment.value())
            if max_payment <= 0:
                QMessageBox.warning(self, 'Warning', 'Maximum monthly payment must be greater than 0')
                return

            # Get selected strategies
            strategies = [key for key, checkbox in self.strategy_checks.items() if checkbox.isChecked()]
            if not strategies:
                QMessageBox.warning(self, 'Warning', 'Please select at least one strategy')
                return

            # Show progress
            self.progress_bar.setVisible(True)
            self.calculate_btn.setEnabled(False)
            self.statusBar.showMessage('Running calculations...')

            # Run in background thread
            self.calculation_thread = QThread()
            self.worker = CalculationWorker(self.calculator, max_payment, strategies)
            self.worker.moveToThread(self.calculation_thread)

            self.worker.progress.connect(self.update_progress)
            self.worker.results.connect(self.on_calculation_complete)
            self.worker.error.connect(self.on_calculation_error)
            self.worker.finished.connect(self.on_calculation_finished)

            self.calculation_thread.started.connect(self.worker.run)
            self.calculation_thread.start()

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Unexpected error: {str(e)}')
            self.statusBar.showMessage(f'Error: {str(e)}')

    def update_progress(self, message):
        """Update progress message."""
        self.statusBar.showMessage(message)

    def on_calculation_complete(self, results):
        """Handle calculation completion."""
        self.calculation_results = results
        self.display_results()
        self.export_summary_btn.setEnabled(True)
        self.export_detailed_btn.setEnabled(True)

    def on_calculation_error(self, error):
        """Handle calculation error."""
        QMessageBox.critical(self, 'Calculation Error', f'Error: {error}')
        self.statusBar.showMessage(f'Error: {error}')

    def on_calculation_finished(self):
        """Handle calculation thread finished."""
        self.progress_bar.setVisible(False)
        self.calculate_btn.setEnabled(True)
        if self.calculation_thread:
            self.calculation_thread.quit()
            self.calculation_thread.wait()

    def display_results(self):
        """Display calculation results in the table."""
        if not self.calculation_results:
            QMessageBox.critical(self, 'Error', 'No results to display')
            return

        try:
            summary = self.calculator.get_summary()

            # Set up table
            self.results_table.setRowCount(len(summary))
            self.results_table.setColumnCount(4)

            row = 0
            for strategy, row_data in summary.iterrows():
                # Strategy name
                item = QTableWidgetItem(str(strategy))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.results_table.setItem(row, 0, item)

                # Months
                item = QTableWidgetItem(f"{row_data['Months to Payoff']:.0f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)
                self.results_table.setItem(row, 1, item)

                # Total Cost
                item = QTableWidgetItem(f"${row_data['Total Cost']:,.2f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(row, 2, item)

                # Total Interest
                item = QTableWidgetItem(f"${row_data['Total Interest']:,.2f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(row, 3, item)

                row += 1

            # Show results
            self.results_title.setVisible(True)
            self.results_table.setVisible(True)
            self.results_table.resizeColumnsToContents()

            self.statusBar.showMessage('Calculations complete!')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error displaying results: {str(e)}')
            self.statusBar.showMessage(f'Error: {str(e)}')

    def export_summary(self):
        """Export summary to file."""
        if not self.calculation_results:
            QMessageBox.warning(self, 'Warning', 'No results to export')
            return

        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, 'Save Summary', '', 'Excel Files (*.xlsx);;CSV Files (*.csv)'
            )

            if filepath:
                if not filepath.lower().endswith(('.xlsx', '.csv')):
                    filepath += '.xlsx'

                self.calculator.export_summary(filepath)
                QMessageBox.information(self, 'Success', f'Summary exported to:\n{filepath}')
                self.statusBar.showMessage('Summary exported successfully')

        except Exception as e:
            QMessageBox.critical(self, 'Export Error', f'Error: {str(e)}')
            self.statusBar.showMessage(f'Export failed: {str(e)}')

    def export_detailed(self):
        """Export detailed results to file."""
        if not self.calculation_results:
            QMessageBox.warning(self, 'Warning', 'No results to export')
            return

        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, 'Save Detailed Results', '', 'Excel Files (*.xlsx);;CSV Files (*.csv)'
            )

            if filepath:
                if not filepath.lower().endswith(('.xlsx', '.csv')):
                    filepath += '.xlsx'

                self.calculator.export_detailed(filepath)
                QMessageBox.information(self, 'Success', f'Detailed results exported to:\n{filepath}')
                self.statusBar.showMessage('Detailed results exported successfully')

        except Exception as e:
            QMessageBox.critical(self, 'Export Error', f'Error: {str(e)}')
            self.statusBar.showMessage(f'Export failed: {str(e)}')

    def clear_form(self):
        """Clear all form fields."""
        self.file_input.clear()
        self.file_status.setText('')
        self.max_payment.setValue(2000)
        self.loan_name_input.clear()
        self.principal_input.setValue(0)
        self.min_payment_input.setValue(0)
        self.interest_rate_input.setValue(0)
        self.manual_loans_table.setRowCount(0)
        self.manual_status.setText('No loans added yet')
        for checkbox in self.strategy_checks.values():
            checkbox.setChecked(True)
        self.results_title.setVisible(False)
        self.results_table.setVisible(False)
        self.export_summary_btn.setEnabled(False)
        self.export_detailed_btn.setEnabled(False)
        self.current_file = None
        self.calculation_results = None
        self.statusBar.showMessage('Cleared')


def main():
    """Entry point for the application."""
    try:
        app = QApplication(sys.argv)
        window = LoanCalculatorApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
