"""
Settlement optimization - minimizes number of transfers to settle debts.
"""
import numpy as np
import pandas as pd
from typing import List

from .models import Group, Settlement
from .expense_calculator import ExpenseCalculator


class SettlementOptimizer:
    """
    Calculates optimal settlements to minimize number of transactions.

    Uses a greedy algorithm that matches largest creditor with largest debtor
    repeatedly until all debts are settled.
    """

    def __init__(self, group: Group):
        self.group = group
        self.calculator = ExpenseCalculator(group)

    def calculate_optimal_settlements(self) -> List[Settlement]:
        """
        Calculate the minimum number of transfers needed to settle all debts.

        Returns:
            List of Settlement objects representing required transfers
        """
        balances_df = self.calculator.get_balances()

        # Create working arrays
        participants = balances_df['participant_id'].tolist()
        balances = balances_df['balance'].to_numpy(dtype=np.float64)

        settlements = []

        # Keep settling until all balances are zero (within tolerance)
        while True:
            # Find max creditor (positive balance) and max debtor (negative balance)
            max_credit_idx = np.argmax(balances)
            max_debit_idx = np.argmin(balances)

            max_credit = balances[max_credit_idx]
            max_debit = balances[max_debit_idx]

            # If no significant debts remain, we're done
            if max_credit < 0.01 and abs(max_debit) < 0.01:
                break

            # Calculate transfer amount
            transfer_amount = min(max_credit, abs(max_debit))
            transfer_amount = np.round(transfer_amount, 2)

            if transfer_amount < 0.01:
                break

            # Record settlement
            settlements.append(Settlement(
                from_participant=participants[max_debit_idx],
                to_participant=participants[max_credit_idx],
                amount=float(transfer_amount),
                currency=self.group.base_currency
            ))

            # Update balances
            balances[max_credit_idx] -= transfer_amount
            balances[max_debit_idx] += transfer_amount

        return settlements

    def get_settlements_dataframe(self) -> pd.DataFrame:
        """
        Get settlements as a formatted DataFrame.

        Returns:
            DataFrame with from, to, amount columns
        """
        settlements = self.calculate_optimal_settlements()

        if not settlements:
            return pd.DataFrame(columns=['from', 'to', 'amount', 'currency'])

        data = []
        for s in settlements:
            from_p = self.group.get_participant_by_id(s.from_participant)
            to_p = self.group.get_participant_by_id(s.to_participant)

            data.append({
                'from': from_p.name if from_p else s.from_participant,
                'to': to_p.name if to_p else s.to_participant,
                'amount': s.amount,
                'currency': s.currency
            })

        return pd.DataFrame(data)

    def get_settlement_summary(self) -> str:
        """
        Get human-readable settlement instructions.

        Returns:
            Formatted string with settlement instructions
        """
        settlements = self.calculate_optimal_settlements()

        if not settlements:
            return "All settled! No payments needed."

        lines = ["Settlements needed:", ""]

        for i, s in enumerate(settlements, 1):
            from_p = self.group.get_participant_by_id(s.from_participant)
            to_p = self.group.get_participant_by_id(s.to_participant)

            from_name = from_p.name if from_p else s.from_participant
            to_name = to_p.name if to_p else s.to_participant

            lines.append(
                f"  {i}. {from_name} pays {to_name}: "
                f"{s.amount:.2f} {s.currency}"
            )

        lines.append("")
        lines.append(f"Total transactions: {len(settlements)}")

        return "\n".join(lines)


def calculate_min_transactions(balances: np.ndarray) -> int:
    """
    Calculate theoretical minimum number of transactions needed.

    This is at most n-1 where n is number of people with non-zero balance.

    Args:
        balances: Array of balances (positive = owed, negative = owes)

    Returns:
        Minimum number of transactions
    """
    non_zero = np.sum(np.abs(balances) > 0.01)
    return max(0, non_zero - 1)
