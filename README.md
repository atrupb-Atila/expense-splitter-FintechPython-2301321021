# Expense Splitter

Smart expense splitting application for groups with complex splitting scenarios.

## Features

- Multiple split methods: equal, percentage, shares, custom
- Optimal settlement calculation (minimizes number of transfers)
- Multi-currency support with real-time exchange rates
- Group analytics and spending patterns

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

## Project Structure

```
expense_splitter/
├── src/
│   ├── main.py              # CLI interface
│   ├── models.py            # Data models
│   ├── expense_calculator.py # Splitting logic
│   ├── settlement.py        # Settlement optimization
│   └── currency.py          # Multi-currency support
├── tests/
│   └── test_expense_splitter.py
├── data/
│   └── sample_data.csv
├── requirements.txt
└── README.md
```

## Technologies

- Python 3.9+
- numpy - numerical calculations
- pandas - data processing
- asyncio/aiohttp - async currency fetching

## Author

Faculty Number: 2301321021
Project: Expense Splitter - Python for Fintech Applications
