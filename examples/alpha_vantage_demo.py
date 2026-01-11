"""Demo script for Alpha Vantage data provider.

This demonstrates:
1. Fetching company fundamentals
2. Getting historical stock data
3. Screening companies by criteria
4. Rate limiting behavior

Requirements:
- Set ALPHA_VANTAGE_API_KEY environment variable
- Free tier allows 5 requests/minute, 500 requests/day

Run with: poetry run python examples/alpha_vantage_demo.py
"""

import asyncio
import os
import sys
from datetime import date, timedelta

from orion.config import DataProviderConfig
from orion.data.models import CompanyOverview
from orion.data.providers.alpha_vantage import AlphaVantageProvider


async def fetch_company_overview(provider: AlphaVantageProvider, symbol: str) -> CompanyOverview:
    """Fetch and display comprehensive company overview."""
    print(f"\nFetching company overview for {symbol}...")
    print("-" * 60)

    overview = await provider.get_company_overview(symbol)

    print(f"Name: {overview.name}")
    print(f"Exchange: {overview.exchange}")
    print(f"Sector: {overview.sector}")
    print(f"Industry: {overview.industry}")
    print()
    print("Financial Metrics:")
    print(f"  Market Cap: ${overview.market_cap:,}" if overview.market_cap else "  Market Cap: N/A")
    print(f"  Revenue (TTM): ${overview.revenue:,}" if overview.revenue else "  Revenue: N/A")
    if overview.revenue_per_share:
        print(f"  Revenue/Share: ${overview.revenue_per_share}")
    if overview.profit_margin:
        print(f"  Profit Margin: {overview.profit_margin:.2%}")
    if overview.operating_margin:
        print(f"  Operating Margin: {overview.operating_margin:.2%}")
    print()
    print("Valuation:")
    if overview.pe_ratio:
        print(f"  P/E Ratio: {overview.pe_ratio:.2f}")
    if overview.peg_ratio:
        print(f"  PEG Ratio: {overview.peg_ratio:.2f}")
    if overview.book_value:
        print(f"  Book Value: ${overview.book_value}")
    if overview.eps:
        print(f"  EPS: ${overview.eps}")
    print()
    print("Growth:")
    if overview.revenue_growth_yoy:
        print(f"  Revenue Growth YoY: {overview.revenue_growth_yoy:.2%}")
    if overview.earnings_growth_yoy:
        print(f"  Earnings Growth YoY: {overview.earnings_growth_yoy:.2%}")
    print()
    print("Risk:")
    if overview.beta:
        print(f"  Beta: {overview.beta:.2f}")
    print()
    print("Price Levels:")
    if overview.week_52_high:
        print(f"  52-Week High: ${overview.week_52_high}")
    if overview.week_52_low:
        print(f"  52-Week Low: ${overview.week_52_low}")
    if overview.moving_average_50:
        print(f"  50-Day MA: ${overview.moving_average_50}")
    if overview.moving_average_200:
        print(f"  200-Day MA: ${overview.moving_average_200}")

    result: CompanyOverview = overview
    return result


async def test_screening_criteria(provider: AlphaVantageProvider) -> None:
    """Test screening multiple companies against criteria."""
    print("\n" + "=" * 60)
    print("Testing Screening Criteria")
    print("=" * 60)

    # Define screening criteria for OFI strategy
    min_revenue = 1_000_000_000  # $1B
    min_market_cap = 10_000_000_000  # $10B

    print("\nScreening Criteria:")
    print(f"  Minimum Revenue: ${min_revenue:,}")
    print(f"  Minimum Market Cap: ${min_market_cap:,}")
    print()

    # Test with several symbols
    symbols = ["IBM", "AAPL", "MSFT"]

    print(f"Testing {len(symbols)} symbols...")
    print("-" * 60)

    for symbol in symbols:
        overview = await provider.get_company_overview(symbol)
        meets = overview.meets_screener_criteria(
            min_revenue=min_revenue, min_market_cap=min_market_cap
        )

        status = "✓ PASS" if meets else "✗ FAIL"
        print(
            f"{symbol:6} {status:8} - Cap: ${overview.market_cap:>15,}, Rev: ${overview.revenue:>15,}"
        )


async def fetch_historical_data(provider: AlphaVantageProvider, symbol: str) -> None:
    """Fetch and analyze historical price data."""
    print("\n" + "=" * 60)
    print(f"Historical Data for {symbol}")
    print("=" * 60)

    end = date.today()
    start = end - timedelta(days=60)

    print(f"\nFetching daily data from {start} to {end}...")
    data = await provider.get_historical_prices(symbol, start, end, interval="1d")

    print(f"Retrieved {len(data)} bars")
    print()
    print("Recent bars:")
    print("Date          Open      High      Low       Close     Volume")
    print("-" * 70)

    # Show last 5 bars
    for bar in data[-5:]:
        print(
            f"{bar.timestamp.date()}  "
            f"${bar.open:>7.2f}  "
            f"${bar.high:>7.2f}  "
            f"${bar.low:>7.2f}  "
            f"${bar.close:>7.2f}  "
            f"{bar.volume:>10,}"
        )

    # Calculate simple metrics
    closes = [float(bar.close) for bar in data]
    avg_close = sum(closes) / len(closes)
    high = max(float(bar.high) for bar in data)
    low = min(float(bar.low) for bar in data)

    print()
    print(f"60-day average close: ${avg_close:.2f}")
    print(f"60-day high: ${high:.2f}")
    print(f"60-day low: ${low:.2f}")
    print(f"Range: {((high - low) / low * 100):.1f}%")


async def main() -> None:
    """Run Alpha Vantage demo."""
    print("#" * 60)
    print("# Alpha Vantage Data Provider Demo")
    print("#" * 60)

    # Check for API key
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("\nERROR: ALPHA_VANTAGE_API_KEY environment variable not set")
        print("\nTo run this demo:")
        print("1. Get a free API key from https://www.alphavantage.co/support/#api-key")
        print("2. Set the environment variable:")
        print("   export ALPHA_VANTAGE_API_KEY=your_key_here")
        print("3. Run the demo again")
        sys.exit(1)

    print(f"\nAPI Key: {api_key[:8]}...{api_key[-4:]}")
    print("\nInitializing provider...")

    # Create provider with rate limiting
    config = DataProviderConfig(api_key=api_key, rate_limit=5)
    provider = AlphaVantageProvider(config)

    print("Rate limit: 5 requests/minute (12 seconds between calls)")

    # Demo 1: Fetch comprehensive company data
    print("\n" + "=" * 60)
    print("Demo 1: Company Fundamentals")
    print("=" * 60)
    await fetch_company_overview(provider, "IBM")

    # Demo 2: Test screening criteria
    await test_screening_criteria(provider)

    # Demo 3: Historical data
    await fetch_historical_data(provider, "IBM")

    print("\n" + "#" * 60)
    print("# Demo Complete!")
    print("#" * 60)
    print("\nNote: Free tier limits:")
    print("  - 5 API calls per minute")
    print("  - 500 API calls per day")
    print("  - Delays between requests are automatically handled")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
