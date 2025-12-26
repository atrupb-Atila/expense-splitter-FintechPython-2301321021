"""
Multi-currency support with async exchange rate fetching.
"""
import asyncio
import aiohttp
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional


class CurrencyConverter:
    """
    Handles currency conversion with real-time exchange rates.

    Uses free API from exchangerate-api.com for rates.
    Implements caching to minimize API calls.
    """

    API_URL = "https://api.exchangerate-api.com/v4/latest/{base}"
    CACHE_DURATION = timedelta(hours=1)

    def __init__(self, base_currency: str = "BGN"):
        self.base_currency = base_currency
        self._rates_cache: Dict[str, float] = {}
        self._cache_timestamp: Optional[datetime] = None

    async def fetch_rates(self) -> Dict[str, float]:
        """
        Fetch current exchange rates from API asynchronously.

        Returns:
            Dict mapping currency codes to rates relative to base currency
        """
        async with aiohttp.ClientSession() as session:
            url = self.API_URL.format(base=self.base_currency)
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self._rates_cache = data.get('rates', {})
                    self._cache_timestamp = datetime.now()
                    return self._rates_cache
                else:
                    raise Exception(f"Failed to fetch rates: {response.status}")

    async def get_rates(self) -> Dict[str, float]:
        """
        Get exchange rates, using cache if valid.

        Returns:
            Dict mapping currency codes to rates
        """
        if self._is_cache_valid():
            return self._rates_cache

        return await self.fetch_rates()

    def _is_cache_valid(self) -> bool:
        """Check if cached rates are still valid."""
        if not self._cache_timestamp or not self._rates_cache:
            return False
        return datetime.now() - self._cache_timestamp < self.CACHE_DURATION

    async def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> float:
        """
        Convert amount between currencies.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount

        rates = await self.get_rates()

        # Convert to base currency first, then to target
        if from_currency == self.base_currency:
            rate = rates.get(to_currency, 1.0)
            return np.round(amount * rate, 2)
        elif to_currency == self.base_currency:
            rate = rates.get(from_currency, 1.0)
            return np.round(amount / rate, 2)
        else:
            # Cross conversion through base currency
            from_rate = rates.get(from_currency, 1.0)
            to_rate = rates.get(to_currency, 1.0)
            base_amount = amount / from_rate
            return np.round(base_amount * to_rate, 2)

    async def convert_multiple(
        self,
        amounts: list[tuple[float, str]]
    ) -> list[float]:
        """
        Convert multiple amounts to base currency concurrently.

        Args:
            amounts: List of (amount, currency) tuples

        Returns:
            List of converted amounts in base currency
        """
        tasks = [
            self.convert(amount, currency, self.base_currency)
            for amount, currency in amounts
        ]
        return await asyncio.gather(*tasks)

    def get_rates_dataframe(self) -> pd.DataFrame:
        """
        Get cached rates as DataFrame.

        Returns:
            DataFrame with currency codes and rates
        """
        if not self._rates_cache:
            return pd.DataFrame(columns=['currency', 'rate'])

        data = [
            {'currency': code, 'rate': rate}
            for code, rate in self._rates_cache.items()
        ]
        return pd.DataFrame(data)


class MultiCurrencyExpenseHandler:
    """
    Handles expenses in multiple currencies.
    """

    def __init__(self, base_currency: str = "BGN"):
        self.base_currency = base_currency
        self.converter = CurrencyConverter(base_currency)

    async def normalize_amounts(
        self,
        expenses: list[dict]
    ) -> pd.DataFrame:
        """
        Convert all expense amounts to base currency.

        Args:
            expenses: List of expense dicts with 'amount' and 'currency' keys

        Returns:
            DataFrame with original and converted amounts
        """
        amounts_to_convert = [
            (exp['amount'], exp['currency'])
            for exp in expenses
        ]

        converted = await self.converter.convert_multiple(amounts_to_convert)

        data = []
        for exp, conv_amount in zip(expenses, converted):
            data.append({
                'description': exp.get('description', ''),
                'original_amount': exp['amount'],
                'original_currency': exp['currency'],
                'converted_amount': conv_amount,
                'base_currency': self.base_currency
            })

        return pd.DataFrame(data)


def run_async(coro):
    """
    Helper to run async functions in sync context.

    Args:
        coro: Coroutine to run

    Returns:
        Result of coroutine
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
