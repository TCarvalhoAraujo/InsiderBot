import pandas as pd

from src.io.cache_manager import load_ohlc_cache

REQUIRED_COLS = [
    # --- Finviz
    "ticker", "insider_name", "relationship", "transaction_date", "transaction_type", 
    "price", "shares", "value", "shares_total", "sec_form4",
    # --- Market Context
    "market_open_at_trade", "market_close_at_trade", "high_at_trade", "low_at_trade",
    "atr_14", "atr_14_pct", "price_prev",
    # --- Outcomes
    "high_plus_7d", "low_plus_7d", "max_gain_7d", "max_drawdown_7d", 
    "high_plus_14d", "low_plus_14d", "max_gain_14d", "max_drawdown_14d", 
    "high_plus_30d", "low_plus_30d", "max_gain_30d", "max_drawdown_30d", 
    "final_gain_30d",
    "outcome_case1", "outcome_case2",
    # --- Meta
    "tags", "footnote_notes", "last_updated",
]

def normalize_schema(df: pd.DataFrame, required_cols=REQUIRED_COLS) -> pd.DataFrame:
    """
    Ensure DataFrame has all required columns with NaN defaults.
    """
    for col in required_cols:
        if col not in df.columns:
            df[col] = pd.NA
    return df[required_cols]

def add_atr(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Adds ATR (Average True Range) and ATR% columns per trade using the OHLC cache.
    Requires at least `window` days of lookback data before each trade date.

    Args:
        df (pd.DataFrame): Trades DataFrame. Must include 'ticker' and 'transaction_date'.
        window (int): Lookback window for ATR calculation (default=14).

    Returns:
        pd.DataFrame: DataFrame with new columns:
            - 'atr_14' (float): Absolute ATR value on trade date.
            - 'atr_14_pct' (float): ATR as percentage of closing price.
    """
    atr_values = []
    atr_pct_values = []

    for _, row in df.iterrows():
        ticker = row["ticker"]
        trade_date = row["transaction_date"].date()

        ohlc = load_ohlc_cache(ticker)
        if ohlc.empty:
            atr_values.append(None)
            atr_pct_values.append(None)
            continue

        # Ensure datetime index
        ohlc["date"] = pd.to_datetime(ohlc["date"]).dt.date
        ohlc = ohlc.sort_values("date")
        ohlc.set_index("date", inplace=True)

        if trade_date not in ohlc.index:
            atr_values.append(None)
            atr_pct_values.append(None)
            continue

        # Slice lookback window: (trade_date - window) → trade_date
        start_idx = ohlc.index.get_loc(trade_date) - window
        end_idx = ohlc.index.get_loc(trade_date)
        if start_idx < 0:
            atr_values.append(None)
            atr_pct_values.append(None)
            continue

        window_data = ohlc.iloc[start_idx:end_idx+1].copy()

        # Compute True Range
        window_data["prev_close"] = window_data["close"].shift(1)
        window_data["tr1"] = window_data["high"] - window_data["low"]
        window_data["tr2"] = (window_data["high"] - window_data["prev_close"]).abs()
        window_data["tr3"] = (window_data["low"] - window_data["prev_close"]).abs()
        window_data["true_range"] = window_data[["tr1", "tr2", "tr3"]].max(axis=1)

        # Compute ATR and ATR%
        atr = window_data["true_range"].rolling(window, min_periods=1).mean().iloc[-1]
        atr_pct = atr / window_data["close"].iloc[-1]

        atr_values.append(atr)
        atr_pct_values.append(atr_pct)

    df["atr_14"] = atr_values
    df["atr_14_pct"] = atr_pct_values

    return df
