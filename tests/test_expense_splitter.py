"""
Tests for the Expense Splitter application.
"""
import unittest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import Group, Participant, Expense, SplitMethod
from src.expense_calculator import ExpenseCalculator
from src.settlement import SettlementOptimizer


class TestModels(unittest.TestCase):
    """Tests for data models."""

    def test_create_participant(self):
        p = Participant(name="Ivan")
        self.assertEqual(p.name, "Ivan")
        self.assertIsNotNone(p.id)

    def test_create_group(self):
        g = Group(name="Test Group")
        self.assertEqual(g.name, "Test Group")
        self.assertEqual(len(g.participants), 0)

    def test_add_participant_to_group(self):
        g = Group(name="Test Group")
        p = g.add_participant("Maria")
        self.assertEqual(len(g.participants), 1)
        self.assertEqual(p.name, "Maria")

    def test_get_participant_by_name(self):
        g = Group(name="Test Group")
        g.add_participant("Ivan")
        g.add_participant("Maria")

        found = g.get_participant_by_name("maria")  # case insensitive
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Maria")


class TestExpenseCalculator(unittest.TestCase):
    """Tests for expense splitting logic."""

    def setUp(self):
        self.group = Group(name="Test Group")
        self.p1 = self.group.add_participant("Ivan")
        self.p2 = self.group.add_participant("Maria")
        self.p3 = self.group.add_participant("Georgi")
        self.calculator = ExpenseCalculator(self.group)

    def test_equal_split(self):
        expense = self.calculator.add_expense_equal(
            description="Dinner",
            total_amount=90.0,
            paid_by=self.p1.id
        )

        self.assertEqual(expense.total_amount, 90.0)
        self.assertEqual(expense.split_method, SplitMethod.EQUAL)
        self.assertEqual(len(expense.splits), 3)

        # Each person owes 30
        for split in expense.splits:
            self.assertEqual(split.amount, 30.0)

    def test_percentage_split(self):
        expense = self.calculator.add_expense_percentage(
            description="Hotel",
            total_amount=100.0,
            paid_by=self.p1.id,
            percentages={
                self.p1.id: 50,
                self.p2.id: 30,
                self.p3.id: 20
            }
        )

        self.assertEqual(expense.split_method, SplitMethod.PERCENTAGE)

        amounts = {s.participant_id: s.amount for s in expense.splits}
        self.assertEqual(amounts[self.p1.id], 50.0)
        self.assertEqual(amounts[self.p2.id], 30.0)
        self.assertEqual(amounts[self.p3.id], 20.0)

    def test_shares_split(self):
        expense = self.calculator.add_expense_shares(
            description="Pizza",
            total_amount=40.0,
            paid_by=self.p2.id,
            shares={
                self.p1.id: 2,
                self.p2.id: 1,
                self.p3.id: 1
            }
        )

        self.assertEqual(expense.split_method, SplitMethod.SHARES)

        amounts = {s.participant_id: s.amount for s in expense.splits}
        self.assertEqual(amounts[self.p1.id], 20.0)  # 2/4 of 40
        self.assertEqual(amounts[self.p2.id], 10.0)  # 1/4 of 40
        self.assertEqual(amounts[self.p3.id], 10.0)  # 1/4 of 40

    def test_balances_calculation(self):
        # Ivan pays 90 for dinner, split equally
        self.calculator.add_expense_equal(
            description="Dinner",
            total_amount=90.0,
            paid_by=self.p1.id
        )

        balances = self.calculator.get_balances()

        ivan_balance = balances[balances['name'] == 'Ivan']['balance'].values[0]
        maria_balance = balances[balances['name'] == 'Maria']['balance'].values[0]
        georgi_balance = balances[balances['name'] == 'Georgi']['balance'].values[0]

        # Ivan paid 90, owes 30, so balance = +60
        self.assertEqual(ivan_balance, 60.0)
        # Maria paid 0, owes 30, so balance = -30
        self.assertEqual(maria_balance, -30.0)
        # Georgi paid 0, owes 30, so balance = -30
        self.assertEqual(georgi_balance, -30.0)

    def test_invalid_percentage(self):
        with self.assertRaises(ValueError):
            self.calculator.add_expense_percentage(
                description="Test",
                total_amount=100.0,
                paid_by=self.p1.id,
                percentages={
                    self.p1.id: 50,
                    self.p2.id: 30  # Only 80%, should fail
                }
            )


class TestSettlementOptimizer(unittest.TestCase):
    """Tests for settlement optimization."""

    def setUp(self):
        self.group = Group(name="Test Group")
        self.p1 = self.group.add_participant("Ivan")
        self.p2 = self.group.add_participant("Maria")
        self.p3 = self.group.add_participant("Georgi")
        self.calculator = ExpenseCalculator(self.group)
        self.optimizer = SettlementOptimizer(self.group)

    def test_no_settlements_needed(self):
        # No expenses, no settlements needed
        settlements = self.optimizer.calculate_optimal_settlements()
        self.assertEqual(len(settlements), 0)

    def test_simple_settlement(self):
        # Ivan pays 60 for everyone (20 each)
        self.calculator.add_expense_equal(
            description="Dinner",
            total_amount=60.0,
            paid_by=self.p1.id
        )

        settlements = self.optimizer.calculate_optimal_settlements()

        # Maria and Georgi each owe Ivan 20
        self.assertEqual(len(settlements), 2)

        total_to_ivan = sum(
            s.amount for s in settlements
            if s.to_participant == self.p1.id
        )
        self.assertEqual(total_to_ivan, 40.0)

    def test_complex_settlement(self):
        # Multiple expenses
        self.calculator.add_expense_equal("Dinner", 90.0, self.p1.id)
        self.calculator.add_expense_equal("Taxi", 30.0, self.p2.id)
        self.calculator.add_expense_equal("Museum", 45.0, self.p3.id)

        settlements = self.optimizer.calculate_optimal_settlements()

        # Verify total balances sum to zero after settlements
        balances = self.calculator.get_balances()
        total_balance = balances['balance'].sum()
        self.assertAlmostEqual(total_balance, 0.0, places=2)

    def test_settlement_minimizes_transactions(self):
        # With 3 people, max 2 transactions needed
        self.calculator.add_expense_equal("Dinner", 90.0, self.p1.id)

        settlements = self.optimizer.calculate_optimal_settlements()
        self.assertLessEqual(len(settlements), 2)


class TestExpenseSummary(unittest.TestCase):
    """Tests for expense summary generation."""

    def setUp(self):
        self.group = Group(name="Test Group")
        self.p1 = self.group.add_participant("Ivan")
        self.p2 = self.group.add_participant("Maria")
        self.calculator = ExpenseCalculator(self.group)

    def test_expense_summary_dataframe(self):
        self.calculator.add_expense_equal("Lunch", 50.0, self.p1.id)
        self.calculator.add_expense_equal("Coffee", 10.0, self.p2.id)

        summary = self.calculator.get_expense_summary()

        self.assertEqual(len(summary), 2)
        self.assertIn('description', summary.columns)
        self.assertIn('amount', summary.columns)
        self.assertIn('paid_by', summary.columns)


if __name__ == '__main__':
    unittest.main()
