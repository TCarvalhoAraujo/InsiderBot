import os
import pandas as pd
from datetime import datetime

RAW_DATA_DIR = "data/raw"
DAILY_DATA_DIR = "data/daily_feed"
FINVIZ_DATA_DIR = "data/finviz"

def ensure_raw_data_dir():
    if not os.path.exists(RAW_DATA_DIR):
        os.makedirs(RAW_DATA_DIR)

def ensure_daily_dir():
    if not os.path.exists(DAILY_DATA_DIR):
        os.makedirs(DAILY_DATA_DIR)

def ensure_finviz_dir():
    if not os.path.exists(FINVIZ_DATA_DIR):
        os.makedirs(FINVIZ_DATA_DIR)

def save_trades_to_csv(ticker: str, trades: list[dict]):
    """
    Saves or appends insider trades to a ticker-specific file under data/raw/.
    Avoids duplicates and keeps data sorted by filing_date.
    """
    ensure_raw_data_dir()
    file_path = os.path.join(RAW_DATA_DIR, f"{ticker.upper()}_trades.csv")

    new_df = pd.DataFrame(trades)
    new_df["filing_date"] = pd.to_datetime(new_df["filing_date"])

    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path, parse_dates=["filing_date"])
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        combined.drop_duplicates(
            subset=["insider_name", "title", "filing_date", "shares", "price", "code"],
            keep="last",
            inplace=True
        )
        combined["filing_date"] = pd.to_datetime(combined["filing_date"])
        combined.sort_values(by="filing_date", ascending=False, inplace=True)
        combined.to_csv(file_path, index=False)
    else:
        new_df.sort_values(by="filing_date", ascending=False, inplace=True)
        new_df.to_csv(file_path, index=False)

def save_daily_trades_to_csv(trades: list[dict], date: datetime):
    """
    Saves all insider trades from a given date to a daily file under data/daily_feed/.
    Appends new trades safely and avoids duplicates.
    """
    ensure_daily_dir()
    date_str = date.strftime("%Y-%m-%d")
    file_path = os.path.join(DAILY_DATA_DIR, f"insider_trades_{date_str}.csv")

    new_df = pd.DataFrame(trades)

    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        combined.drop_duplicates(
            subset=["insider_name", "title", "filing_date", "shares", "price", "code", "filing_url"],
            keep="last",
            inplace=True
        )
        combined["filing_date"] = pd.to_datetime(combined["filing_date"])
        combined.sort_values(by="filing_date", ascending=False, inplace=True)
        combined.to_csv(file_path, index=False)
    else:
        new_df.sort_values(by="filing_date", ascending=False, inplace=True)
        new_df.to_csv(file_path, index=False)

    print(f"✅ Saved {len(trades)} new trades to {file_path}")

def get_latest_filing_date(ticker: str) -> datetime | None:
    """
    Returns the most recent filing date for a given ticker, or None if no file exists.
    """
    file_path = os.path.join(RAW_DATA_DIR, f"{ticker.upper()}_trades.csv")
    if not os.path.exists(file_path):
        return None

    try:
        df = pd.read_csv(file_path, parse_dates=["filing_date"])
    except Exception as e:
        print(f"⚠️ Failed to read {file_path}: {e}")
        return None

    if "filing_date" not in df.columns:
        print(f"⚠️ No 'filing_date' column in {file_path}")
        return None

    df = df.dropna(subset=["filing_date"])
    if df.empty:
        return None

    return df["filing_date"].max()

def save_finviz_trades_to_csv(new_trades: pd.DataFrame):
    ensure_finviz_dir()

    today_str = datetime.today().strftime("%Y-%m-%d")
    daily_file = os.path.join(FINVIZ_DATA_DIR, f"{today_str}_finviz.csv")
    master_file = os.path.join(FINVIZ_DATA_DIR, "finviz_all_trades.csv")

    # Save today's file
    new_trades.to_csv(daily_file, index=False)

    # Merge with existing master file
    if os.path.exists(master_file):
        existing = pd.read_csv(master_file, parse_dates=["transaction_date"])
        combined = pd.concat([existing, new_trades], ignore_index=True)
    else:
        combined = new_trades.copy()

    combined.drop_duplicates(
        subset=["ticker", "insider_name", "relationship", "transaction_date", "transaction_type", "price", "shares", "sec_form4"],
        inplace=True
    )

    # Sort by date descending
    combined.sort_values(by="transaction_date", ascending=False, inplace=True)

    # Save updated master file
    combined.to_csv(master_file, index=False)

def load_latest_tagged_trades(filename: str = "tagged_trades.csv") -> pd.DataFrame:
    """
    Loads the most recent tagged_trades CSV from disk.
    """
    path = os.path.join(FINVIZ_DATA_DIR, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Tagged trades file not found: {path}")
    
    df = pd.read_csv(path)
    print(f"📥 Loaded {len(df)} tagged trades from {filename}")
    return df