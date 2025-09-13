from src.preparation.cleaner import pre_ohlc_noise_reduction, drop_split_merger_anomalies, drop_low_atr_trades
from src.preparation.data_preparation import add_atr


def pre_ohlc_filter(df, snapshot_cache, min_market_cap=150_000_000):
    """
    Filters a DataFrame of trades using snapshot metadata.

    Args:
        df (pd.DataFrame): Trades DataFrame.
        snapshot_cache (dict): Snapshot metadata keyed by ticker.
        min_market_cap (int): Minimum allowed market cap.

    Returns:
        pd.DataFrame: Filtered DataFrame with only valid tickers.
    """
    tickers = df["ticker"].unique()
    valid_tickers = pre_ohlc_noise_reduction(tickers, snapshot_cache, min_market_cap)
    return df[df["ticker"].isin(valid_tickers)].copy()

def post_ohlc_filter(df, split_threshold=1.70, min_atr_pct=0.02):
    """
    Reduces noise after OHLC enrichment:
    - Drops split/merger anomalies (insider price vs open)
    - Drops low ATR% trades

    Args:
        df (pd.DataFrame): Trades DataFrame with OHLC features.
        split_threshold (float): Threshold for anomaly detection (default=1.70).
        min_atr_pct (float): Minimum ATR% required (default=0.02 = 2%).

    Returns:
        pd.DataFrame: Cleaned DataFrame after OHLC noise reduction.
    """
    df = add_atr(df, window=14)
    df = drop_split_merger_anomalies(df, threshold=split_threshold)
    df = drop_low_atr_trades(df, min_atr_pct=min_atr_pct)
    return df