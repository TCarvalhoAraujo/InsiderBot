import os
import json
import pandas as pd

CACHE_DIR = "data/finviz/cache"
OHLC_CACHE_DIR = "data/finviz/cache/ohlc"

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def ensure_ohlc_dir():
    if not os.path.exists(OHLC_CACHE_DIR):
        os.makedirs(OHLC_CACHE_DIR)

def load_snapshot_cache() -> dict:
    """
    Loads snapshot cache from disk if available.

    Returns:
        dict: Cached snapshot data keyed by ticker.
    """
    ensure_cache_dir()
    cache_path = os.path.join(CACHE_DIR, "snapshot.json")

    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}

def save_snapshot_cache(cache: dict) -> None:
    """
    Saves snapshot cache to disk as JSON.

    Args:
        cache (dict): Snapshot data keyed by ticker.

    Returns:
        None
    """
    ensure_cache_dir()
    cache_path = os.path.join(CACHE_DIR, "snapshot.json")

    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2, default=str)
    print(f"📦 Snapshot cache saved to {cache_path} ({len(cache)} tickers)")

def get_ohlc_cache_path(ticker: str) -> str:
    ensure_ohlc_dir()
    return os.path.join(OHLC_CACHE_DIR, f"{ticker.upper()}.csv")

def load_ohlc_cache(ticker: str) -> pd.DataFrame:
    """
    Loads OHLC (Open, High, Low, Close, Volume) data for a ticker from cache.

    Args:
        ticker (str): Stock ticker symbol.

    Returns:
        pd.DataFrame: DataFrame with OHLC data. Columns include:
            - date (datetime.date)
            - open, high, low, close, volume (floats)
            - price_prev (float): Previous day's close
    """
    path = get_ohlc_cache_path(ticker)

    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["date"])
        df["date"] = df["date"].dt.date

        if not df.empty:
            df = df.sort_values("date")

            updated = False

            # Ensure prev price column exists
            if "price_prev" not in df.columns:
                df["price_prev"] = df["close"].shift(1)
                updated = True

            if updated:
                save_ohlc_cache(ticker, df)

        return df

    # If file doesn't exist, return empty DataFrame with schema
    return pd.DataFrame(columns=[
        "date", "open", "high", "low", "close", "volume", "price_prev"
    ])


def save_ohlc_cache(ticker: str, df: pd.DataFrame) -> None:
    """
    Saves OHLC data for a ticker into cache, ensuring no duplicate dates.

    Args:
        ticker (str): Stock ticker symbol.
        df (pd.DataFrame): DataFrame with OHLC data.

    Returns:
        None
    """
    path = get_ohlc_cache_path(ticker)
    df = df.drop_duplicates(subset="date")
    df = df.sort_values("date")
    df.to_csv(path, index=False)
    print(f"📦 OHLC cache saved: {ticker} ({len(df)} rows)")
