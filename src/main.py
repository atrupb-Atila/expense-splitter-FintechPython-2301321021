"""
Expense Splitter - CLI Interface

A smart expense splitting application for groups.
"""
import sys
from typing import Optional

from .models import Group, SplitMethod
from .expense_calculator import ExpenseCalculator
from .settlement import SettlementOptimizer
from .currency import CurrencyConverter, run_async


class ExpenseSplitterApp:
    """Main application class for the Expense Splitter."""

    def __init__(self):
        self.group: Optional[Group] = None
        self.calculator: Optional[ExpenseCalculator] = None
        self.optimizer: Optional[SettlementOptimizer] = None
        self.converter: Optional[CurrencyConverter] = None

    def create_group(self, name: str, base_currency: str = "BGN") -> None:
        """Create a new expense group."""
        self.group = Group(name=name, base_currency=base_currency)
        self.calculator = ExpenseCalculator(self.group)
        self.optimizer = SettlementOptimizer(self.group)
        self.converter = CurrencyConverter(base_currency)
        print(f"Created group: {name}")

    def add_participant(self, name: str) -> None:
        """Add a participant to the group."""
        if not self.group:
            print("Error: Create a group first!")
            return
        p = self.group.add_participant(name)
        print(f"Added: {name} (ID: {p.id})")

    def add_expense(
        self,
        description: str,
        amount: float,
        paid_by_name: str,
        split_method: str = "equal",
        split_data: Optional[dict] = None
    ) -> None:
        """Add an expense to the group."""
        if not self.group or not self.calculator:
            print("Error: Create a group first!")
            return

        payer = self.group.get_participant_by_name(paid_by_name)
        if not payer:
            print(f"Error: Participant '{paid_by_name}' not found!")
            return

        try:
            if split_method == "equal":
                self.calculator.add_expense_equal(
                    description=description,
                    total_amount=amount,
                    paid_by=payer.id
                )
            elif split_method == "percentage":
                if not split_data:
                    print("Error: Percentage split requires split_data!")
                    return
                # Convert names to IDs
                pct_by_id = {}
                for name, pct in split_data.items():
                    p = self.group.get_participant_by_name(name)
                    if p:
                        pct_by_id[p.id] = pct
                self.calculator.add_expense_percentage(
                    description=description,
                    total_amount=amount,
                    paid_by=payer.id,
                    percentages=pct_by_id
                )
            elif split_method == "shares":
                if not split_data:
                    print("Error: Shares split requires split_data!")
                    return
                shares_by_id = {}
                for name, shares in split_data.items():
                    p = self.group.get_participant_by_name(name)
                    if p:
                        shares_by_id[p.id] = shares
                self.calculator.add_expense_shares(
                    description=description,
                    total_amount=amount,
                    paid_by=payer.id,
                    shares=shares_by_id
                )
            elif split_method == "custom":
                if not split_data:
                    print("Error: Custom split requires split_data!")
                    return
                custom_by_id = {}
                for name, amt in split_data.items():
                    p = self.group.get_participant_by_name(name)
                    if p:
                        custom_by_id[p.id] = amt
                self.calculator.add_expense_custom(
                    description=description,
                    total_amount=amount,
                    paid_by=payer.id,
                    custom_amounts=custom_by_id
                )
            else:
                print(f"Error: Unknown split method '{split_method}'")
                return

            print(f"Added expense: {description} ({amount:.2f} {self.group.base_currency})")

        except ValueError as e:
            print(f"Error: {e}")

    def show_balances(self) -> None:
        """Display current balances for all participants."""
        if not self.calculator:
            print("Error: Create a group first!")
            return

        print("\n--- Balances ---")
        df = self.calculator.get_balances()
        if df.empty:
            print("No data")
            return

        for _, row in df.iterrows():
            balance = row['balance']
            status = "owes" if balance < 0 else "is owed"
            print(f"  {row['name']}: {status} {abs(balance):.2f}")
        print()

    def show_expenses(self) -> None:
        """Display all expenses."""
        if not self.calculator:
            print("Error: Create a group first!")
            return

        print("\n--- Expenses ---")
        df = self.calculator.get_expense_summary()
        if df.empty:
            print("No expenses recorded")
            return

        for _, row in df.iterrows():
            print(f"  [{row['split_method']}] {row['description']}: "
                  f"{row['amount']:.2f} (paid by {row['paid_by']})")
        print()

    def show_settlements(self) -> None:
        """Display optimal settlements."""
        if not self.optimizer:
            print("Error: Create a group first!")
            return

        print(self.optimizer.get_settlement_summary())

    def convert_currency(self, amount: float, from_curr: str, to_curr: str) -> None:
        """Convert amount between currencies."""
        if not self.converter:
            self.converter = CurrencyConverter()

        try:
            result = run_async(self.converter.convert(amount, from_curr, to_curr))
            print(f"{amount:.2f} {from_curr} = {result:.2f} {to_curr}")
        except Exception as e:
            print(f"Error converting currency: {e}")

    def show_exchange_rates(self) -> None:
        """Fetch and display current exchange rates."""
        if not self.converter:
            self.converter = CurrencyConverter()

        try:
            run_async(self.converter.fetch_rates())
            df = self.converter.get_rates_dataframe()
            print(f"\n--- Exchange Rates (base: {self.converter.base_currency}) ---")
            common = ['USD', 'EUR', 'GBP', 'BGN', 'RON', 'TRY']
            for _, row in df.iterrows():
                if row['currency'] in common:
                    print(f"  {row['currency']}: {row['rate']:.4f}")
            print()
        except Exception as e:
            print(f"Error fetching rates: {e}")


def interactive_mode():
    """Run the application in interactive mode."""
    app = ExpenseSplitterApp()

    print("=" * 50)
    print("  Expense Splitter - Interactive Mode")
    print("=" * 50)
    print("\nCommands:")
    print("  group <name>          - Create new group")
    print("  add <name>            - Add participant")
    print("  expense <desc> <amt> <payer> - Add equal split expense")
    print("  balances              - Show balances")
    print("  expenses              - Show all expenses")
    print("  settle                - Show settlements")
    print("  rates                 - Show exchange rates")
    print("  convert <amt> <from> <to> - Convert currency")
    print("  quit                  - Exit")
    print()

    while True:
        try:
            cmd = input("> ").strip().split()
            if not cmd:
                continue

            action = cmd[0].lower()

            if action == "quit" or action == "exit":
                print("Goodbye!")
                break
            elif action == "group" and len(cmd) >= 2:
                app.create_group(" ".join(cmd[1:]))
            elif action == "add" and len(cmd) >= 2:
                app.add_participant(" ".join(cmd[1:]))
            elif action == "expense" and len(cmd) >= 4:
                desc = cmd[1]
                amt = float(cmd[2])
                payer = " ".join(cmd[3:])
                app.add_expense(desc, amt, payer)
            elif action == "balances":
                app.show_balances()
            elif action == "expenses":
                app.show_expenses()
            elif action == "settle":
                app.show_settlements()
            elif action == "rates":
                app.show_exchange_rates()
            elif action == "convert" and len(cmd) == 4:
                amt = float(cmd[1])
                app.convert_currency(amt, cmd[2].upper(), cmd[3].upper())
            else:
                print("Unknown command. Type 'quit' to exit.")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def demo():
    """Run a demonstration of the expense splitter."""
    print("=" * 50)
    print("  Expense Splitter - Demo")
    print("=" * 50)

    app = ExpenseSplitterApp()

    # Create group
    app.create_group("Trip to Plovdiv")

    # Add participants
    app.add_participant("Ivan")
    app.add_participant("Maria")
    app.add_participant("Georgi")

    # Add expenses
    app.add_expense("Dinner", 90.00, "Ivan")
    app.add_expense("Taxi", 30.00, "Maria")
    app.add_expense("Museum tickets", 45.00, "Georgi")
    app.add_expense("Drinks", 60.00, "Ivan")

    # Show results
    app.show_expenses()
    app.show_balances()
    app.show_settlements()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        interactive_mode()
