import argparse
import pandas as pd

from src.handler.finviz_handler import finviz_daily_scan
from src.handler.yahooquery_handler import build_snapshot_cache
from src.preparation.data_preparation import normalize_schema

# ---------------------------------------- #
#              DAILY PIPELINE              #
# ---------------------------------------- #
def run_daily_pipeline():
    """
    Daily run follows the flow:
    -> Scan from Finviz
    -> Merge and Save New Trades
    -> Normalize Schema
    -> Update Company Information for New Tickers
    -> Clean Up .CSV
    -> Update OHLC from the Past 14d for New Tickers
    -> Tag All Trades
    -> Extract Footnotes from SEC Filing
    -> Prepare and Save All Trades for Prediction
    -> Save Results
    """

    # 1. Scan + Merge + Save + Normalize
    df_new = finviz_daily_scan()
    if df_new.empty:
        print("No new trades today. Exiting...")
        return
    
    # 2. Normalize new Trades
    df_new = normalize_schema(df_new)

    # 3. Build Snapshot Cache
    snapshot_cache = build_snapshot_cache(df_new["ticker"].unique())

    




# ---------------------------------------- #
#             WEEKLY PIPELINE              #
# ---------------------------------------- #

def run_weekly_pipeline():
    """
    Weekly run follows the flow:
    -> Gets Trades Without Outcome Tags
    -> Updates OHLC
    -> Try to Update Outcome Tags Based on New OHLC Data
    -> Prepare and Save Results for Training
    """
    pass


# ---------------------------------------- #
#               ENTRY POINT                #
# ---------------------------------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InsiderBot Pipelines")
    parser.add_argument(
        "mode",
        choices=["daily", "weekly"],
        help="Which pipeline to run (daily or weekly)"
    )
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily_pipeline()
    elif args.mode == "weekly":
        run_weekly_pipeline()