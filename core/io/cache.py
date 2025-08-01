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

def load_snapshot_cache():
    ensure_cache_dir()

    cache_path = os.path.join(CACHE_DIR, "snapshot.json")

    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}

def save_snapshot_cache(cache: dict):
    ensure_cache_dir()

    cache_path = os.path.join(CACHE_DIR, "snapshot.json")

    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2, default=str)
    print(f"📦 Snapshot cache saved to {cache_path} ({len(cache)} tickers)")

def get_ohlc_cache_path(ticker: str) -> str:
    ensure_ohlc_dir()
    return os.path.join(OHLC_CACHE_DIR, f"{ticker.upper()}.csv")

def load_ohlc_cache(ticker: str) -> pd.DataFrame:
    path = get_ohlc_cache_path(ticker)
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["date"])
        df["date"] = df["date"].dt.date
        return df
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

def save_ohlc_cache(ticker: str, df: pd.DataFrame):
    path = get_ohlc_cache_path(ticker)
    df = df.drop_duplicates(subset="date")
    df = df.sort_values("date")
    df.to_csv(path, index=False)
    print(f"📦 OHLC cache saved: {ticker} ({len(df)} days)")