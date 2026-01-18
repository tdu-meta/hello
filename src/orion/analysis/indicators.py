"""
Technical indicator calculations using pandas-ta.

This module provides the IndicatorCalculator class for computing various technical
indicators from OHLCV data, including moving averages, RSI, and volume averages.
"""


import pandas as pd
import pandas_ta as ta

from orion.data.models import OHLCV, TechnicalIndicators
from orion.utils.logging import get_logger

logger = get_logger(__name__, component="IndicatorCalculator")


class IndicatorCalculator:
    """
    Calculate technical indicators from historical OHLCV data.

    This calculator uses the pandas-ta library to efficiently compute
    technical indicators including Simple Moving Averages (SMA),
    Relative Strength Index (RSI), and volume averages.

    Example:
        >>> calculator = IndicatorCalculator()
        >>> indicators = calculator.calculate(ohlcv_list, "AAPL")
        >>> print(indicators.sma_20, indicators.rsi_14)
    """

    def __init__(self) -> None:
        """Initialize the IndicatorCalculator."""
        self._logger = logger

    def calculate(self, ohlcv_list: list[OHLCV], symbol: str) -> TechnicalIndicators:
        """
        Calculate technical indicators from a list of OHLCV data.

        Args:
            ohlcv_list: List of OHLCV objects, sorted chronologically
            symbol: Stock symbol for the indicators

        Returns:
            TechnicalIndicators dataclass with calculated values.
            Indicator values will be None if insufficient data is available.

        Raises:
            ValueError: If ohlcv_list is empty

        Note:
            Minimum data requirements:
            - SMA-20: 20 data points
            - SMA-60: 60 data points
            - RSI-14: 15 data points (pandas-ta needs warmup period)
            - Volume avg-20: 20 data points
        """
        if not ohlcv_list:
            self._logger.warning("empty_ohlcv_list", symbol=symbol)
            raise ValueError(f"Cannot calculate indicators for {symbol}: OHLCV list is empty")

        data_points = len(ohlcv_list)
        timestamp = ohlcv_list[-1].timestamp

        # Log if we have limited data
        if data_points < 60:
            self._logger.info(
                "limited_data_for_indicators",
                symbol=symbol,
                data_points=data_points,
                note="Full indicator calculation requires at least 60 data points",
            )

        # Convert OHLCV list to pandas DataFrame
        df = self._ohlcv_to_dataframe(ohlcv_list)

        # Calculate indicators
        sma_20 = self._calculate_sma(df, period=20)
        sma_60 = self._calculate_sma(df, period=60)
        rsi_14 = self._calculate_rsi(df, period=14)
        volume_avg_20 = self._calculate_volume_avg(df, period=20)

        indicators = TechnicalIndicators(
            symbol=symbol,
            timestamp=timestamp,
            sma_20=sma_20,
            sma_60=sma_60,
            rsi_14=rsi_14,
            volume_avg_20=volume_avg_20,
        )

        self._logger.debug(
            "indicators_calculated",
            symbol=symbol,
            sma_20=sma_20,
            sma_60=sma_60,
            rsi_14=rsi_14,
            volume_avg_20=volume_avg_20,
        )

        return indicators

    def _ohlcv_to_dataframe(self, ohlcv_list: list[OHLCV]) -> pd.DataFrame:
        """
        Convert a list of OHLCV objects to a pandas DataFrame.

        Args:
            ohlcv_list: List of OHLCV objects

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        data = {
            "timestamp": [bar.timestamp for bar in ohlcv_list],
            "open": [float(bar.open) for bar in ohlcv_list],
            "high": [float(bar.high) for bar in ohlcv_list],
            "low": [float(bar.low) for bar in ohlcv_list],
            "close": [float(bar.close) for bar in ohlcv_list],
            "volume": [bar.volume for bar in ohlcv_list],
        }
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df

    def _calculate_sma(self, df: pd.DataFrame, period: int) -> float | None:
        """
        Calculate Simple Moving Average.

        Args:
            df: DataFrame with OHLCV data
            period: SMA period

        Returns:
            Latest SMA value or None if insufficient data
        """
        if len(df) < period:
            return None

        try:
            sma = ta.sma(df["close"], length=period)
            latest = sma.iloc[-1]
            return float(latest) if pd.notna(latest) else None
        except Exception as e:
            self._logger.error("sma_calculation_failed", period=period, error=str(e))
            return None

    def _calculate_rsi(self, df: pd.DataFrame, period: int) -> float | None:
        """
        Calculate Relative Strength Index.

        Args:
            df: DataFrame with OHLCV data
            period: RSI period

        Returns:
            Latest RSI value or None if insufficient data
        """
        # pandas-ta RSI needs at least period+1 data points
        if len(df) < period + 1:
            return None

        try:
            rsi = ta.rsi(df["close"], length=period)
            latest = rsi.iloc[-1]
            return float(latest) if pd.notna(latest) else None
        except Exception as e:
            self._logger.error("rsi_calculation_failed", period=period, error=str(e))
            return None

    def _calculate_volume_avg(self, df: pd.DataFrame, period: int) -> float | None:
        """
        Calculate volume moving average.

        Args:
            df: DataFrame with OHLCV data
            period: Averaging period

        Returns:
            Latest volume average value or None if insufficient data
        """
        if len(df) < period:
            return None

        try:
            vol_avg = ta.sma(df["volume"], length=period)
            latest = vol_avg.iloc[-1]
            return float(latest) if pd.notna(latest) else None
        except Exception as e:
            self._logger.error("volume_avg_calculation_failed", period=period, error=str(e))
            return None
