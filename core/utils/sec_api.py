from bs4 import BeautifulSoup
from datetime import datetime
import requests
from time import sleep

from core.fetch_xml import get_primary_xml
from core.parse_filing import parse_insider_trade
from config.constants import HEADERS

def get_trades_from_last_year(ticker_or_cik: str, since: datetime, limit: int = 100) -> list[dict]:
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker_or_cik}&type=4&owner=only&count={limit}&output=atom"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"Failed to fetch Atom feed for {ticker_or_cik}")
        return []

    soup = BeautifulSoup(res.content, "xml")
    entries = soup.find_all("entry")
    trades = []

    for entry in entries:
        try:
            updated_str = entry.find("updated").text
            filing_date = datetime.strptime(updated_str[:10], "%Y-%m-%d")
            if filing_date < since:
                continue

            index_url = entry.find("link")["href"]
            xml_url = get_primary_xml(index_url)
            if not xml_url:
                continue

            filing_trades = parse_insider_trade(xml_url)
            for t in filing_trades:
                t["filing_date"] = filing_date.strftime("%Y-%m-%d")
            trades.extend(filing_trades)

            sleep(1)
        except Exception as e:
            print(f"Error processing entry: {e}")
            continue

    return trades

def get_daily_trades(target_date: datetime, count=100):
    """
    Pulls all insider trades filed on a specific day (using the global SEC Atom feed).
    Returns the list of parsed trades. Optionally saves to CSV.
    """

    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count={count}&output=atom"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"❌ Failed to fetch Atom feed: {res.status_code}")
        return []

    soup = BeautifulSoup(res.content, "xml")
    entries = soup.find_all("entry")

    all_trades = []
    target_str = target_date.strftime("%Y-%m-%d")

    for entry in entries:
        try:
            updated = entry.find("updated").text[:10]
            if updated != target_str:
                continue

            index_url = entry.find("link")["href"]
            xml_url = get_primary_xml(index_url)
            if not xml_url:
                continue

            trades = parse_insider_trade(xml_url)
            for t in trades:
                t["filing_date"] = target_str
                t["filing_url"] = index_url
            all_trades.extend(trades)
            sleep(1)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            continue

    if not all_trades:
        print(f"⚠️ No trades found for {target_str}")

    return all_trades
