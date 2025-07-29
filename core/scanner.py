import json
from datetime import datetime, timedelta
from time import sleep

from core.io.file_manager import get_latest_filing_date, save_trades_to_csv, save_daily_trades_to_csv, save_finviz_trades_to_csv
from core.sec_controller import get_company_trades, get_daily_trades
from core.finviz_scraper import finviz_scraper

def scan_all_companies_from_json(json_path: str, limit_per_feed: int = 100):
    with open(json_path, "r") as f:
        companies = json.load(f)

    print(f"🔍 Scanning {len(companies)} companies...")

    for entry in companies:
        ticker = entry["ticker"]
        name =  entry["name"]
        print(f"\n🚨 {ticker} ({name})")

        latest_date = get_latest_filing_date(ticker)
        if latest_date is None:
            latest_date = datetime.now() - timedelta(days=365)
            print("  ➤ No previous data. Starting from 1 year ago.")
        else:
            print(f"  ➤ Last filing date: {latest_date.date()}")

        sleep(1)
        trades = get_company_trades(ticker, since=latest_date, limit=limit_per_feed)

        if trades:
            print(f"  ✅ {len(trades)} trades fetched. Saving...")
            save_trades_to_csv(ticker, trades)
        else:
            print("  ⚠️  No new trades found.")

def daily_run():
    today = datetime.today().date()
    print(f"📅 Running daily insider scan for {today}...")

    trades = get_daily_trades(today)

    if not trades:
        print("⚠️ No insider trades found for today.")
        return

    save_daily_trades_to_csv(trades, today)
    print(f"✅ Daily run completed. {len(trades)} trades saved.")

def scan_for_company():
    """
    Prompts user for a ticker, then scans and saves insider trades for that company.
    """
    ticker = input("Enter the TICKER (e.g., AAPL): ").upper().strip()
    print(f"\n🔍 Running scan for {ticker}...\n")

    latest_date = get_latest_filing_date(ticker)
    if latest_date is None:
        latest_date = datetime.now() - timedelta(days=365)
        print("  ➤ No previous data. Starting from 1 year ago.")
    else:
        print(f"  ➤ Last filing date: {latest_date.date()}")

    trades = get_company_trades(ticker, since=latest_date, limit=50)

    if trades:
        print(f"  ✅ {len(trades)} trades fetched. Saving...")
        save_trades_to_csv(ticker, trades)
    else:
        print("  ⚠️  No new trades found.")

def scan_from_finviz():
    """
    Scans the Finviz insider trading page for recent BUY trades only,
    and saves them to the data/finviz/ folder with deduplication.
    """
    print("\n🔍 Scanning Finviz for insider BUY trades...\n")
    
    try:
        trades = finviz_scraper()
        if not trades.empty:
            print(f"  ✅ {len(trades)} trades fetched. Saving to CSV...")
            save_finviz_trades_to_csv(trades)
            print("  📁 Saved and merged to data/finviz/")
        else:
            print("  ⚠️  No trades found on Finviz.")
    except Exception as e:
        print(f"  ❌ An error occurred during scan: {e}")