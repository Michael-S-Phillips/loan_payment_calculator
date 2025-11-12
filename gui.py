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
    QMessageBox, QStatusBar, QProgressBar, QHeaderView, QDialog, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QColor

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from loan_calculator import LoanCalculator
from plot_strategies import StrategyPlotter


class CalculationWorker(QObject):
    """Worker for running calculations in background thread."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    strategy_progress = pyqtSignal(str, int, int)  # strategy_name, current, total
    results = pyqtSignal(dict)

    def __init__(self, calculator, max_payment, strategies):
        super().__init__()
        self.calculator = calculator
        self.max_payment = max_payment
        self.strategies = strategies

    def on_strategy_progress(self, strategy_name, current, total):
        """Handle progress update from calculator."""
        self.strategy_progress.emit(strategy_name, current, total)
        self.progress.emit(f'Calculating: {strategy_name} ({current}/{total})')

    def run(self):
        """Run the calculation."""
        try:
            self.progress.emit('Starting calculations...')
            results = self.calculator.calculate(
                max_monthly_payment=self.max_payment,
                payment_case=0,  # Fixed total payment
                strategies=self.strategies,
                progress_callback=self.on_strategy_progress
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

    def setup_stylesheet(self):
        """Apply stylesheet that works with light and dark themes."""
        stylesheet = """
            QMainWindow {
                background-color: palette(window);
                color: palette(text);
            }

            QWidget {
                background-color: palette(window);
                color: palette(text);
            }

            QLabel {
                color: palette(text);
            }

            /* Guidance boxes with proper contrast */
            QLabel#guidance_box {
                background-color: palette(button);
                color: palette(text);
                border: 1px solid palette(mid);
                padding: 10px;
                border-radius: 4px;
            }

            QPushButton {
                background-color: palette(button);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 5px;
                min-width: 60px;
            }

            QPushButton:hover {
                background-color: palette(alternate-base);
            }

            QPushButton:pressed {
                background-color: palette(mid);
            }

            /* Green button for Calculate */
            QPushButton#calculate_btn {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
            }

            QPushButton#calculate_btn:hover {
                background-color: #45a049;
            }

            QLineEdit {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                padding: 5px;
                border-radius: 3px;
            }

            QDoubleSpinBox, QSpinBox {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                padding: 5px;
                border-radius: 3px;
            }

            QCheckBox {
                color: palette(text);
                spacing: 5px;
            }

            QRadioButton {
                color: palette(text);
                spacing: 5px;
            }

            QTableWidget {
                background-color: palette(base);
                color: palette(text);
                gridline-color: palette(mid);
                border: 1px solid palette(mid);
            }

            QTableWidget::item {
                padding: 5px;
                border-right: 1px solid palette(mid);
                border-bottom: 1px solid palette(mid);
            }

            QHeaderView::section {
                background-color: palette(button);
                color: palette(text);
                padding: 5px;
                border: 1px solid palette(mid);
            }

            QProgressBar {
                border: 1px solid palette(mid);
                border-radius: 4px;
                background-color: palette(base);
                text-align: center;
                color: palette(text);
            }

            QProgressBar::chunk {
                background-color: #4CAF50;
            }

            QTabWidget::pane {
                border: 1px solid palette(mid);
            }

            QTabBar::tab {
                background-color: palette(button);
                color: palette(text);
                padding: 6px 20px;
                border: 1px solid palette(mid);
            }

            QTabBar::tab:selected {
                background-color: palette(base);
                border-bottom: 2px solid #4CAF50;
            }

            QTabBar::tab:hover {
                background-color: palette(alternate-base);
            }

            QStatusBar {
                color: palette(text);
            }

            QMessageBox QLabel {
                color: palette(text);
            }

            /* Subtitle text with muted color */
            QLabel#subtitle {
                color: palette(mid);
                font-size: 10px;
            }

            /* File status label - green for success */
            QLabel#file_status {
                color: #4CAF50;
                font-weight: bold;
            }
        """
        self.setStyleSheet(stylesheet)

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Loan Payment Calculator')
        self.setGeometry(100, 100, 1400, 1100)

        # Apply modern stylesheet that works with light and dark themes
        self.setup_stylesheet()

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
        subtitle.setObjectName('subtitle')
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(10)

        # Loan Data Section
        self.create_loan_data_section(main_layout)

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
            ('snowball', 'Snowball Method - Pay off lowest balance loans first'),
            ('milp_lifetime', '⭐ MILP Lifetime Optimal - Globally optimal solution')
        ]

        for key, label in strategies:
            checkbox = QCheckBox(label)
            checkbox.setChecked(key != 'milp_lifetime')  # Enable all except MILP by default
            self.strategy_checks[key] = checkbox
            strategy_layout.addWidget(checkbox)

        main_layout.addLayout(strategy_layout)
        main_layout.addSpacing(10)

        # Action buttons
        button_layout = QHBoxLayout()
        self.calculate_btn = QPushButton('Calculate')
        self.calculate_btn.setObjectName('calculate_btn')
        self.calculate_btn.clicked.connect(self.calculate)
        button_layout.addWidget(self.calculate_btn)

        self.export_summary_btn = QPushButton('Export Summary')
        self.export_summary_btn.clicked.connect(self.export_summary)
        self.export_summary_btn.setEnabled(False)
        button_layout.addWidget(self.export_summary_btn)

        self.export_detailed_btn = QPushButton('Export Detailed')
        self.export_detailed_btn.clicked.connect(self.export_detailed)
        self.export_detailed_btn.setEnabled(False)
        button_layout.addWidget(self.export_detailed_btn)

        self.view_plots_btn = QPushButton('View Plots')
        self.view_plots_btn.clicked.connect(self.view_plots)
        self.view_plots_btn.setEnabled(False)
        self.view_plots_btn.setStyleSheet('QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }')
        button_layout.addWidget(self.view_plots_btn)

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
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(['Strategy', 'Months', 'Total Principal', 'Total Interest', 'Total Cost'])
        self.results_table.setRowCount(0)
        self.results_table.setVisible(False)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.results_table)

        main_layout.addStretch()

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')

    def create_loan_data_section(self, parent_layout):
        """Create unified loan data section with editable table."""
        # Guidance
        guidance = QLabel(
            'Enter your loan information below. You can either upload a file, generate a template to fill in, or manually add loans to the table.\n'
            'All table fields are editable. Required columns: Principal Balance, Minimum Monthly Payment, Annual Interest Rate %'
        )
        guidance.setObjectName('guidance_box')
        parent_layout.addWidget(guidance)

        parent_layout.addSpacing(10)

        # File upload section
        file_layout = QHBoxLayout()

        template_btn = QPushButton('Generate Template')
        template_btn.clicked.connect(self.generate_template)
        file_layout.addWidget(template_btn)

        file_layout.addWidget(QLabel('Or upload:'))
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_input.setPlaceholderText('No file selected')
        file_layout.addWidget(self.file_input)

        self.browse_btn = QPushButton('Browse')
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)

        parent_layout.addLayout(file_layout)

        parent_layout.addSpacing(10)

        # Loan data table
        self.loan_data_title = QLabel('Loan Information')
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.loan_data_title.setFont(title_font)
        parent_layout.addWidget(self.loan_data_title)

        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(7)
        self.loans_table.setHorizontalHeaderLabels([
            'Loan #', 'Description', 'Type', 'Term (mo)', 'Principal', 'Min Payment', 'Interest Rate %'
        ])
        self.loans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.loans_table.setMinimumHeight(150)
        parent_layout.addWidget(self.loans_table)

        parent_layout.addSpacing(5)

        # Add loan form
        form_layout = QHBoxLayout()

        form_layout.addWidget(QLabel('Add Loan:'))

        form_layout.addWidget(QLabel('Description:'))
        self.loan_description_input = QLineEdit()
        self.loan_description_input.setPlaceholderText('e.g., Student Loan A')
        form_layout.addWidget(self.loan_description_input)

        form_layout.addWidget(QLabel('Type:'))
        self.loan_type_input = QLineEdit()
        self.loan_type_input.setPlaceholderText('e.g., Federal')
        form_layout.addWidget(self.loan_type_input)

        form_layout.addWidget(QLabel('Principal:'))
        self.principal_input = QDoubleSpinBox()
        self.principal_input.setMaximum(999999999)
        form_layout.addWidget(self.principal_input)

        form_layout.addWidget(QLabel('Min Payment:'))
        self.min_payment_input = QDoubleSpinBox()
        self.min_payment_input.setMaximum(999999)
        form_layout.addWidget(self.min_payment_input)

        form_layout.addWidget(QLabel('Interest %:'))
        self.interest_rate_input = QDoubleSpinBox()
        self.interest_rate_input.setMaximum(100)
        self.interest_rate_input.setDecimals(2)
        form_layout.addWidget(self.interest_rate_input)

        self.add_loan_btn = QPushButton('Add')
        self.add_loan_btn.clicked.connect(self.add_loan_to_table)
        form_layout.addWidget(self.add_loan_btn)

        parent_layout.addLayout(form_layout)

        parent_layout.addSpacing(5)

        # Table management buttons
        button_layout = QHBoxLayout()

        self.remove_loan_btn = QPushButton('Remove Selected Row')
        self.remove_loan_btn.clicked.connect(self.remove_selected_row)
        button_layout.addWidget(self.remove_loan_btn)

        self.clear_table_btn = QPushButton('Clear All')
        self.clear_table_btn.clicked.connect(self.clear_loans_table)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_table_btn)

        parent_layout.addLayout(button_layout)

    def generate_template(self):
        """Generate a template file."""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, 'Save Template File', 'loan_template.xlsx', 'Excel Files (*.xlsx)'
            )
            if filepath:
                self.calculator.create_template_file(filepath)
                QMessageBox.information(self, 'Success', f'Template file created:\n{filepath}')
                self.statusBar.showMessage('Template file generated')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error creating template: {str(e)}')

    def browse_file(self):
        """Browse for a loan data file and automatically load it."""
        file_filter = 'All Files (*);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;TSV Files (*.tsv);;Text Files (*.txt)'
        filepath, _ = QFileDialog.getOpenFileName(self, 'Load Loan Data', '', file_filter)
        if filepath:
            self.file_input.setText(filepath)
            # Automatically load the file after selection
            self.load_file()

    def load_file(self):
        """Load the selected file and populate the table."""
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

            # Populate the table from loaded data
            self.populate_loans_table(self.calculator.loan_data)

            self.current_file = filepath
            filename = Path(filepath).name
            self.statusBar.showMessage(f'Loaded: {filename}')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error loading file: {str(e)}')
            self.statusBar.showMessage(f'Error: {str(e)}')

    def populate_loans_table(self, df):
        """Populate the loans table from a DataFrame."""
        try:
            self.loans_table.setRowCount(len(df))

            for row, (_, loan_row) in enumerate(df.iterrows()):
                # Loan #
                loan_num_item = QTableWidgetItem(str(loan_row.iloc[0]))
                self.loans_table.setItem(row, 0, loan_num_item)

                # Description (column 1)
                desc_item = QTableWidgetItem(str(loan_row.iloc[1]))
                self.loans_table.setItem(row, 1, desc_item)

                # Type (column 2)
                type_item = QTableWidgetItem(str(loan_row.iloc[2]))
                self.loans_table.setItem(row, 2, type_item)

                # Term (column 3)
                term_item = QTableWidgetItem(str(int(loan_row.iloc[3])))
                self.loans_table.setItem(row, 3, term_item)

                # Principal (column 4)
                principal_item = QTableWidgetItem(f'{float(loan_row.iloc[4]):,.2f}')
                self.loans_table.setItem(row, 4, principal_item)

                # Min Payment (column 5)
                payment_item = QTableWidgetItem(f'{float(loan_row.iloc[5]):,.2f}')
                self.loans_table.setItem(row, 5, payment_item)

                # Interest Rate (column 6)
                rate_item = QTableWidgetItem(f'{float(loan_row.iloc[6]):.2f}')
                self.loans_table.setItem(row, 6, rate_item)

            self.statusBar.showMessage(f'Table updated: {len(df)} loan(s)')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error populating table: {str(e)}')

    def add_loan_to_table(self):
        """Add a loan from the form to the table."""
        try:
            description = self.loan_description_input.text().strip()
            loan_type = self.loan_type_input.text().strip()
            principal = self.principal_input.value()
            min_payment = self.min_payment_input.value()
            interest_rate = self.interest_rate_input.value()

            if not description:
                QMessageBox.warning(self, 'Warning', 'Please enter a loan description')
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

            # Add new row
            row = self.loans_table.rowCount()
            self.loans_table.insertRow(row)

            # Loan # (auto-increment)
            loan_num = self.loans_table.rowCount()
            self.loans_table.setItem(row, 0, QTableWidgetItem(str(loan_num)))

            # Description
            self.loans_table.setItem(row, 1, QTableWidgetItem(description))

            # Type
            self.loans_table.setItem(row, 2, QTableWidgetItem(loan_type))

            # Term (default 0)
            self.loans_table.setItem(row, 3, QTableWidgetItem('0'))

            # Principal
            self.loans_table.setItem(row, 4, QTableWidgetItem(f'{principal:,.2f}'))

            # Min Payment
            self.loans_table.setItem(row, 5, QTableWidgetItem(f'{min_payment:,.2f}'))

            # Interest Rate
            self.loans_table.setItem(row, 6, QTableWidgetItem(f'{interest_rate:.2f}'))

            # Clear inputs
            self.loan_description_input.clear()
            self.loan_type_input.clear()
            self.principal_input.setValue(0)
            self.min_payment_input.setValue(0)
            self.interest_rate_input.setValue(0)

            self.statusBar.showMessage(f'Loan added: {self.loans_table.rowCount()} total loans')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error adding loan: {str(e)}')

    def remove_selected_row(self):
        """Remove the selected row from the table."""
        current_row = self.loans_table.currentRow()
        if current_row >= 0:
            self.loans_table.removeRow(current_row)
            self.statusBar.showMessage(f'Row removed: {self.loans_table.rowCount()} loans remaining')
        else:
            QMessageBox.warning(self, 'Warning', 'Please select a row to remove')

    def clear_loans_table(self):
        """Clear all rows from the loans table."""
        reply = QMessageBox.question(
            self, 'Confirm Clear',
            'Are you sure you want to clear all loans?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.loans_table.setRowCount(0)
            self.statusBar.showMessage('Table cleared')

    def get_loan_data(self):
        """Get loan data from the table."""
        if self.loans_table.rowCount() == 0:
            QMessageBox.warning(self, 'Warning', 'Please add at least one loan to the table')
            return None

        try:
            import pandas as pd

            loans = []
            for row in range(self.loans_table.rowCount()):
                loan_num = self.loans_table.item(row, 0).text()
                description = self.loans_table.item(row, 1).text()
                loan_type = self.loans_table.item(row, 2).text()
                term = self.loans_table.item(row, 3).text()
                principal = float(self.loans_table.item(row, 4).text().replace(',', ''))
                min_payment = float(self.loans_table.item(row, 5).text().replace(',', ''))
                interest_rate = float(self.loans_table.item(row, 6).text())

                loans.append({
                    'Loan Number': int(loan_num) if loan_num.isdigit() else row + 1,
                    'Description': description,
                    'Loan Type': loan_type,
                    'Term': int(term) if term.isdigit() else 0,
                    'Principal': principal,
                    'Min Payment': min_payment,
                    'Interest Rate': interest_rate
                })

            data = pd.DataFrame(loans)
            self.calculator.loan_data = data
            return data

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error reading table data: {str(e)}')
            return None

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
            self.worker.strategy_progress.connect(self.update_strategy_progress)
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

    def update_strategy_progress(self, strategy_name, current, total):
        """Update progress bar based on strategy progress."""
        # Set progress bar to show percentage completion
        percentage = int((current / total) * 100)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(percentage)

    def on_calculation_complete(self, results):
        """Handle calculation completion."""
        self.calculation_results = results
        self.display_results()
        self.export_summary_btn.setEnabled(True)
        self.export_detailed_btn.setEnabled(True)
        self.view_plots_btn.setEnabled(True)

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
            self.results_table.setColumnCount(5)

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

                # Total Principal (calculated as Total Cost - Total Interest)
                principal = row_data['Total Cost'] - row_data['Total Interest']
                item = QTableWidgetItem(f"${principal:,.2f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(row, 2, item)

                # Total Interest
                item = QTableWidgetItem(f"${row_data['Total Interest']:,.2f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(row, 3, item)

                # Total Cost
                item = QTableWidgetItem(f"${row_data['Total Cost']:,.2f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(row, 4, item)

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
            QMessageBox.warning(self, 'Warning', 'No results to export. Please run calculations first.')
            return

        if self.calculator.summary is None:
            QMessageBox.warning(self, 'Warning', 'Summary data not available. Please run calculations first.')
            return

        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, 'Save Summary', '', 'Excel Files (*.xlsx);;CSV Files (*.csv)'
            )

            if not filepath:
                self.statusBar.showMessage('Export cancelled')
                return

            if not filepath.lower().endswith(('.xlsx', '.csv')):
                filepath += '.xlsx'

            self.calculator.export_summary(filepath)
            QMessageBox.information(self, 'Success', f'Summary exported to:\n{filepath}')
            self.statusBar.showMessage('Summary exported successfully')

        except Exception as e:
            QMessageBox.critical(self, 'Export Error', f'Error exporting summary: {str(e)}')
            self.statusBar.showMessage(f'Export failed: {str(e)}')

    def export_detailed(self):
        """Export detailed results to file."""
        if not self.calculation_results:
            QMessageBox.warning(self, 'Warning', 'No results to export. Please run calculations first.')
            return

        if not self.calculator.results:
            QMessageBox.warning(self, 'Warning', 'Detailed results not available. Please run calculations first.')
            return

        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, 'Save Detailed Results', '', 'Excel Files (*.xlsx);;CSV Files (*.csv)'
            )

            if not filepath:
                self.statusBar.showMessage('Export cancelled')
                return

            if not filepath.lower().endswith(('.xlsx', '.csv')):
                filepath += '.xlsx'

            self.calculator.export_detailed(filepath)
            QMessageBox.information(self, 'Success', f'Detailed results exported to:\n{filepath}')
            self.statusBar.showMessage('Detailed results exported successfully')

        except Exception as e:
            QMessageBox.critical(self, 'Export Error', f'Error exporting detailed results: {str(e)}')
            self.statusBar.showMessage(f'Export failed: {str(e)}')

    def view_plots(self):
        """Display strategy comparison plots."""
        if not self.calculator.results:
            QMessageBox.warning(self, 'Warning', 'No results to plot. Please run calculations first.')
            return

        try:
            # Create a dialog window for the plots
            plot_dialog = QDialog(self)
            plot_dialog.setWindowTitle('Loan Payment Strategy Comparison - Plots')
            plot_dialog.setGeometry(100, 100, 1400, 900)

            # Create matplotlib figure
            fig = StrategyPlotter.create_comparison_plots(self.calculator.results)

            # Create canvas and add to dialog
            canvas = FigureCanvas(fig)
            layout = QVBoxLayout()
            layout.addWidget(canvas)

            # Add a close button
            close_btn = QPushButton('Close')
            close_btn.clicked.connect(plot_dialog.accept)
            layout.addWidget(close_btn)

            plot_dialog.setLayout(layout)
            plot_dialog.exec_()

            self.statusBar.showMessage('Plots displayed successfully')

        except Exception as e:
            QMessageBox.critical(self, 'Plot Error', f'Error displaying plots: {str(e)}')
            self.statusBar.showMessage(f'Plot failed: {str(e)}')

    def clear_form(self):
        """Clear all form fields and tables."""
        self.file_input.clear()
        self.max_payment.setValue(2000)
        self.loan_description_input.clear()
        self.loan_type_input.clear()
        self.principal_input.setValue(0)
        self.min_payment_input.setValue(0)
        self.interest_rate_input.setValue(0)
        self.loans_table.setRowCount(0)
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
