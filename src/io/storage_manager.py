import os
from datetime import datetime
import pandas as pd

from src.preparation.data_preparation import normalize_schema

FINVIZ_DATA_DIR = "data/finviz/daily_scans"

def ensure_finviz_dir():
    if not os.path.exists(FINVIZ_DATA_DIR):
        os.makedirs(FINVIZ_DATA_DIR)
        
def save_finviz_trades_to_csv(new_trades: pd.DataFrame) -> None:
    """
    Saves Finviz trades to daily + master files with deduplication.

    Args:
        new_trades (pd.DataFrame): DataFrame of new Finviz trades scraped today.

    Returns:
        None: Updates the daily snapshot file and the master file on disk.
    """
    ensure_finviz_dir()

    today_str = datetime.today().strftime("%Y-%m-%d")
    timestamp_str = datetime.now().strftime("%H-%M-%S")

    # Daily snapshot with timestamp (keeps all intraday scans)
    daily_file = os.path.join(FINVIZ_DATA_DIR, f"{today_str}_{timestamp_str}_finviz.csv")
    master_file = os.path.join(FINVIZ_DATA_DIR, "finviz_all_trades.csv")

    # Save intraday snapshot
    new_trades.to_csv(daily_file, index=False)

    # Merge with master file
    if os.path.exists(master_file):
        existing = pd.read_csv(master_file, parse_dates=["transaction_date"])
        combined = pd.concat([existing, new_trades], ignore_index=True)
    else:
        combined = new_trades.copy()

    # Deduplicate
    combined.drop_duplicates(
        subset=[
            "ticker", "insider_name", "relationship",
            "transaction_date", "transaction_type",
            "price", "shares", "sec_form4"
        ],
        inplace=True
    )

    # Sort by date (descending)
    combined.sort_values(by="transaction_date", ascending=False, inplace=True)

    # Normalize
    combined = normalize_schema(combined)

    # Save back to master file
    combined.to_csv(master_file, index=False)

    print(f"  📁 Saved {len(combined)} total trades to {master_file}")
