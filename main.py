from core.scanner import scan_all_companies_from_json, daily_run, scan_for_company, scan_from_finviz
from core.engine.analyzer import analyze_finviz_trade
from core.io.file_manager import load_finviz_all_trades
from core.engine.ohlc import update_ohlc
from core.engine.summary import generate_trade_md
from core.engine.backtest import run_backtest_pipeline

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def print_main_menu():
    print("\n📊 INSIDERBOT MENU")
    print("1 - Run daily insider trade scan (global Atom feed)")
    print("2 - Run full company scan (based on tickers.json)")
    print("3 - Run scan from finviz website (filters only buys)")
    print("4 - Tag trades from finviz")
    print("5 - Update OHLC data")
    print("6 - Run Backtest")
    print("7 - Generate Summary File")
    print("0 - Exit")

def print_company_menu():
    print("\n🏢 FULL COMPANY SCAN")
    print("1 - Run Small Caps")
    print("2 - Run Top 50 Companies")
    print("3 - Run for a specific company")
    print("0 - Return to Main Menu")

def handle_company_scan():
    while True:
        print_company_menu()
        sub_choice = input("Enter your choice: ").strip()

        if sub_choice == "1":
            path = os.path.join(BASE_DIR, "config", "small_caps.json")
            scan_all_companies_from_json(path, limit_per_feed=50)

        elif sub_choice == "2":
            path = os.path.join(BASE_DIR, "config", "top_50.json")
            scan_all_companies_from_json(path, limit_per_feed=50)

        elif sub_choice == "3":
            scan_for_company()

        elif sub_choice == "0":
            return  # Go back to main menu

        else:
            print("❌ Invalid option. Please choose 1, 2, 3, or 0.")

def main():
    while True:
        print_main_menu()
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            daily_run()

        elif choice == "2":
            handle_company_scan()

        elif choice == "3":
            scan_from_finviz()

        elif choice == "4":
            analyze_finviz_trade()

        elif choice == "5":
            df = load_finviz_all_trades()
            update_ohlc(df)

        elif choice == "6":
            run_backtest_pipeline()

        elif choice == "7": 
            print("=== Insider Trade Markdown Generator ===")

            # Collect inputs from user
            ticker = input("Ticker: ").upper()
            insider_price = float(input("Insider Buy Price: "))
            current_price = float(input("Current Stock Price: "))
            num_stocks = int(input("How many stocks will you buy: "))
            date = input("Date (YYYY-MM-DD): ")
            sma9 = float(input("SMA 9 (daily candles): "))
            rsi14 = float(input("RSI 14 (daily candles): "))

            # Optional fields
            tags_input = input("Tags (comma separated, optional): ").strip()
            tags = [t.strip() for t in tags_input.split(",")] if tags_input else []

            news_input = input("News (semicolon separated, optional): ").strip()
            news = [n.strip() for n in news_input.split(";")] if news_input else []

            # Call generator
            filename = generate_trade_md(
                                    ticker=ticker,
                                    insider_price=insider_price,
                                    current_price=current_price,
                                    num_stocks=num_stocks,
                                    date=date,
                                    sma9=sma9,
                                    rsi14=rsi14,
                                    tags=tags,
                                    news=news
                                )

            print(f"\n✅ Trade card saved to {filename}")

        elif choice == "0":
            print("👋 Exiting InsiderBot. Have a great day!")
            break

        else:
            print("❌ Invalid option.")

if __name__ == "__main__":
    main()