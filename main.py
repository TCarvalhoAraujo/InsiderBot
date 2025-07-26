from core.scanner import scan_all_companies_from_json, daily_run, scan_for_company, scan_from_finviz
import os

# ticker = "AMZN"
# 
# latest_date = get_latest_filing_date(ticker)
# if latest_date is None:
#     print("No previous data. Using 1 year ago.")
#     latest_date = datetime.now() - timedelta(days=365)
# 
# print(f"Checking filings since: {latest_date.date()}")
# 
# trades = get_trades_from_atom_since(ticker, since=latest_date)
# 
# print(f"Fetched {len(trades)} new trades.")
# save_trades_to_csv(ticker, trades)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def print_main_menu():
    print("\n📊 INSIDERBOT MENU")
    print("1 - Run daily insider trade scan (global Atom feed)")
    print("2 - Run full company scan (based on tickers.json)")
    print("3 - Run scan from finviz website (filters only buys)")
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

        elif choice == "0":
            print("👋 Exiting InsiderBot. Have a great day!")
            break

        else:
            print("❌ Invalid option. Please choose 1, 2, or 0.")

if __name__ == "__main__":
    main()