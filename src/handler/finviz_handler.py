import pandas as pd

from src.extraction.finviz import finviz_scraper
from src.io.storage_manager import save_finviz_trades_to_csv

def finviz_daily_scan() -> pd.DataFrame:
    """
    Scans the Finviz insider trading page for recent BUY trades only,
    saves them to daily + master CSVs, and returns the new trades DataFrame.

    Args:
        None

    Returns:
        pd.DataFrame: DataFrame containing the new trades scraped from Finviz.
                      Empty if no trades are found or if an error occurs.
    """
    print("\n🔍 Scanning Finviz for insider BUY trades...\n")

    try:
        trades = finviz_scraper()
        if trades.empty:
            print("  ⚠️ No trades found on Finviz.")
            return pd.DataFrame()

        print(f"  ✅ {len(trades)} trades fetched. Saving to CSV...")
        save_finviz_trades_to_csv(trades)

        # Return new trades for enrichment/tagging
        return trades

    except Exception as e:
        print(f"  ❌ An error occurred during scan: {e}")
        return pd.DataFrame()
