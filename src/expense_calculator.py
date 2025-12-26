"""
Expense splitting logic with support for multiple split methods.
"""
import numpy as np
import pandas as pd
from typing import Optional

from .models import Group, Expense, ExpenseSplit, SplitMethod, Participant


class ExpenseCalculator:
    """Handles expense splitting calculations for a group."""

    def __init__(self, group: Group):
        self.group = group

    def add_expense_equal(
        self,
        description: str,
        total_amount: float,
        paid_by: str,
        participants: Optional[list[str]] = None,
        currency: str = "BGN",
        category: Optional[str] = None
    ) -> Expense:
        """
        Add an expense split equally among participants.

        Args:
            description: What the expense is for
            total_amount: Total cost
            paid_by: ID of participant who paid
            participants: List of participant IDs to split among (default: all)
            currency: Currency code
            category: Optional category
        """
        if participants is None:
            participants = [p.id for p in self.group.participants]

        n = len(participants)
        amount_per_person = np.round(total_amount / n, 2)

        # Handle rounding remainder
        amounts = np.full(n, amount_per_person)
        remainder = total_amount - np.sum(amounts)
        if remainder != 0:
            amounts[0] += np.round(remainder, 2)

        splits = [
            ExpenseSplit(participant_id=pid, amount=float(amt))
            for pid, amt in zip(participants, amounts)
        ]

        expense = Expense(
            description=description,
            total_amount=total_amount,
            paid_by=paid_by,
            currency=currency,
            split_method=SplitMethod.EQUAL,
            splits=splits,
            category=category
        )

        self.group.expenses.append(expense)
        return expense

    def add_expense_percentage(
        self,
        description: str,
        total_amount: float,
        paid_by: str,
        percentages: dict[str, float],
        currency: str = "BGN",
        category: Optional[str] = None
    ) -> Expense:
        """
        Add an expense split by percentages.

        Args:
            description: What the expense is for
            total_amount: Total cost
            paid_by: ID of participant who paid
            percentages: Dict mapping participant_id to percentage (should sum to 100)
            currency: Currency code
            category: Optional category
        """
        pct_array = np.array(list(percentages.values()))

        if not np.isclose(pct_array.sum(), 100.0):
            raise ValueError(f"Percentages must sum to 100, got {pct_array.sum()}")

        splits = []
        for pid, pct in percentages.items():
            amount = np.round(total_amount * (pct / 100), 2)
            splits.append(ExpenseSplit(
                participant_id=pid,
                amount=float(amount),
                percentage=pct
            ))

        expense = Expense(
            description=description,
            total_amount=total_amount,
            paid_by=paid_by,
            currency=currency,
            split_method=SplitMethod.PERCENTAGE,
            splits=splits,
            category=category
        )

        self.group.expenses.append(expense)
        return expense

    def add_expense_shares(
        self,
        description: str,
        total_amount: float,
        paid_by: str,
        shares: dict[str, int],
        currency: str = "BGN",
        category: Optional[str] = None
    ) -> Expense:
        """
        Add an expense split by shares.

        Args:
            description: What the expense is for
            total_amount: Total cost
            paid_by: ID of participant who paid
            shares: Dict mapping participant_id to number of shares
            currency: Currency code
            category: Optional category
        """
        shares_array = np.array(list(shares.values()))
        total_shares = shares_array.sum()

        splits = []
        for pid, share_count in shares.items():
            amount = np.round(total_amount * (share_count / total_shares), 2)
            splits.append(ExpenseSplit(
                participant_id=pid,
                amount=float(amount),
                shares=share_count
            ))

        expense = Expense(
            description=description,
            total_amount=total_amount,
            paid_by=paid_by,
            currency=currency,
            split_method=SplitMethod.SHARES,
            splits=splits,
            category=category
        )

        self.group.expenses.append(expense)
        return expense

    def add_expense_custom(
        self,
        description: str,
        total_amount: float,
        paid_by: str,
        custom_amounts: dict[str, float],
        currency: str = "BGN",
        category: Optional[str] = None
    ) -> Expense:
        """
        Add an expense with custom amounts per person.

        Args:
            description: What the expense is for
            total_amount: Total cost
            paid_by: ID of participant who paid
            custom_amounts: Dict mapping participant_id to exact amount
            currency: Currency code
            category: Optional category
        """
        amounts_array = np.array(list(custom_amounts.values()))

        if not np.isclose(amounts_array.sum(), total_amount):
            raise ValueError(
                f"Custom amounts must sum to total ({total_amount}), "
                f"got {amounts_array.sum()}"
            )

        splits = [
            ExpenseSplit(participant_id=pid, amount=float(amt))
            for pid, amt in custom_amounts.items()
        ]

        expense = Expense(
            description=description,
            total_amount=total_amount,
            paid_by=paid_by,
            currency=currency,
            split_method=SplitMethod.CUSTOM,
            splits=splits,
            category=category
        )

        self.group.expenses.append(expense)
        return expense

    def get_balances(self) -> pd.DataFrame:
        """
        Calculate current balance for each participant.

        Positive balance = others owe them money
        Negative balance = they owe money to others

        Returns:
            DataFrame with participant balances
        """
        balances = {p.id: 0.0 for p in self.group.participants}

        for expense in self.group.expenses:
            # Person who paid gets credit for the full amount
            balances[expense.paid_by] += expense.total_amount

            # Each person owes their split
            for split in expense.splits:
                balances[split.participant_id] -= split.amount

        # Build DataFrame
        data = []
        for p in self.group.participants:
            data.append({
                'participant_id': p.id,
                'name': p.name,
                'balance': np.round(balances[p.id], 2)
            })

        return pd.DataFrame(data)

    def get_expense_summary(self) -> pd.DataFrame:
        """Get summary of all expenses."""
        if not self.group.expenses:
            return pd.DataFrame()

        data = []
        for exp in self.group.expenses:
            payer = self.group.get_participant_by_id(exp.paid_by)
            data.append({
                'id': exp.id,
                'description': exp.description,
                'amount': exp.total_amount,
                'currency': exp.currency,
                'paid_by': payer.name if payer else exp.paid_by,
                'split_method': exp.split_method.value,
                'date': exp.date,
                'category': exp.category
            })

        return pd.DataFrame(data)
