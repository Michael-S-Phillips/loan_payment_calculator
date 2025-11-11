"""
PyQt5 application for loan payment calculator.

Provides a professional interface for loading loan data, running calculations,
and exporting results.
"""

import sys
import os
from pathlib import Path
import traceback
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QCheckBox, QRadioButton, QButtonGroup, QSpinBox, QDoubleSpinBox,
    QMessageBox, QStatusBar, QGroupBox, QGridLayout, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from loan_calculator import LoanCalculator


class LoanCalculatorApp(QMainWindow):
    """Main application window for Loan Payment Calculator."""

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.calculator = LoanCalculator()
        self.current_file = None
        self.calculation_results = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Loan Payment Calculator')
        self.setGeometry(100, 100, 1000, 900)

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

        # Step 1: Load Data
        section1_title = QLabel('Step 1: Load Loan Data')
        section1_title_font = QFont()
        section1_title_font.setPointSize(12)
        section1_title_font.setBold(True)
        section1_title.setFont(section1_title_font)
        main_layout.addWidget(section1_title)

        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel('Input File:'))
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        file_layout.addWidget(self.file_input)
        self.browse_btn = QPushButton('Browse')
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        main_layout.addLayout(file_layout)

        load_layout = QHBoxLayout()
        self.load_btn = QPushButton('Load File')
        self.load_btn.clicked.connect(self.load_file)
        load_layout.addWidget(self.load_btn)
        self.file_status = QLabel('')
        self.file_status.setStyleSheet('color: green;')
        load_layout.addWidget(self.file_status)
        load_layout.addStretch()
        main_layout.addLayout(load_layout)

        main_layout.addSpacing(10)

        # Step 2: Parameters
        section2_title = QLabel('Step 2: Set Payment Parameters')
        section2_title.setFont(section1_title_font)
        main_layout.addWidget(section2_title)

        params_layout = QGridLayout()

        params_layout.addWidget(QLabel('Maximum Monthly Payment:'), 0, 0)
        self.max_payment = QDoubleSpinBox()
        self.max_payment.setValue(2000)
        self.max_payment.setMinimum(0)
        self.max_payment.setMaximum(999999)
        params_layout.addWidget(self.max_payment, 0, 1)
        params_layout.addWidget(QLabel('(total amount available each month)'), 0, 2)

        params_layout.addWidget(QLabel('Payment Case:'), 1, 0)
        self.payment_case_group = QButtonGroup()
        self.case0_radio = QRadioButton('Fixed total payment (payment covers interest + principal)')
        self.case0_radio.setChecked(True)
        self.case1_radio = QRadioButton('Fixed principal payment (total = interest + fixed amount)')
        self.payment_case_group.addButton(self.case0_radio, 0)
        self.payment_case_group.addButton(self.case1_radio, 1)
        params_layout.addWidget(self.case0_radio, 2, 0, 1, 3)
        params_layout.addWidget(self.case1_radio, 3, 0, 1, 3)

        main_layout.addLayout(params_layout)
        main_layout.addSpacing(10)

        # Step 3: Strategies
        section3_title = QLabel('Step 3: Select Strategies')
        section3_title.setFont(section1_title_font)
        main_layout.addWidget(section3_title)

        strategy_layout = QGridLayout()
        self.strategy_checks = {}
        strategies = [
            ('even', 'Even Payments'),
            ('high_interest', 'High Interest First'),
            ('high_balance', 'High Balance First'),
            ('minimize_interest', 'Minimize Interest'),
            ('snowball', 'Snowball Method')
        ]

        for i, (key, label) in enumerate(strategies):
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            self.strategy_checks[key] = checkbox
            strategy_layout.addWidget(checkbox, i // 2, i % 2)

        main_layout.addLayout(strategy_layout)
        main_layout.addSpacing(10)

        # Action buttons
        button_layout = QHBoxLayout()
        self.calculate_btn = QPushButton('Calculate')
        self.calculate_btn.clicked.connect(self.calculate)
        self.calculate_btn.setStyleSheet('background-color: green; color: white; font-weight: bold;')
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

        # Results section
        results_title = QLabel('Results Summary')
        results_title.setFont(section1_title_font)
        results_title.setVisible(False)
        self.results_title = results_title
        main_layout.addWidget(results_title)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(['Strategy', 'Months', 'Total Cost', 'Total Interest'])
        self.results_table.setRowCount(0)
        self.results_table.setVisible(False)
        self.results_table.resizeColumnsToContents()
        main_layout.addWidget(self.results_table)

        main_layout.addStretch()

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')

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

    def calculate(self):
        """Run the calculations."""
        if not self.current_file:
            QMessageBox.warning(self, 'Warning', 'Please load a file first')
            return

        try:
            # Get parameters
            max_payment = float(self.max_payment.value())
            if max_payment <= 0:
                QMessageBox.warning(self, 'Warning', 'Maximum monthly payment must be greater than 0')
                return

            payment_case = self.payment_case_group.checkedId()

            # Get selected strategies
            strategies = [key for key, checkbox in self.strategy_checks.items() if checkbox.isChecked()]

            if not strategies:
                QMessageBox.warning(self, 'Warning', 'Please select at least one strategy')
                return

            self.statusBar.showMessage('Calculating... Please wait')
            QApplication.processEvents()

            # Run calculations
            self.calculation_results = self.calculator.calculate(
                max_monthly_payment=max_payment,
                payment_case=payment_case,
                strategies=strategies
            )

            # Display results
            self.display_results()

            # Enable export buttons
            self.export_summary_btn.setEnabled(True)
            self.export_detailed_btn.setEnabled(True)

        except ValueError as e:
            QMessageBox.critical(self, 'Calculation Error', f'Error: {str(e)}')
            self.statusBar.showMessage(f'Error: {str(e)}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Unexpected error: {str(e)}\n\n{traceback.format_exc()}')
            self.statusBar.showMessage(f'Error: {str(e)}')

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
                    if filepath.endswith('.'):
                        filepath = filepath[:-1] + '.xlsx'
                    else:
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
                    if filepath.endswith('.'):
                        filepath = filepath[:-1] + '.xlsx'
                    else:
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
        self.case0_radio.setChecked(True)
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
