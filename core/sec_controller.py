from bs4 import BeautifulSoup
from datetime import datetime, date
import requests
from time import sleep

from config.constants import HEADERS
from core.utils.utils import safe_get_text

def get_company_trades(ticker_or_cik: str, since: datetime, limit: int = 100) -> list[dict]:
    """
    Fetches insider trades (Form 4) for a specific company since a given date.
    """
    
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
            filing_date = _get_filing_date_from_entry(entry)
            if filing_date < since.date():
                continue

            index_url = entry.find("link")["href"]
            xml_url = _get_primary_xml(index_url)
            if not xml_url:
                continue

            filing_trades = _parse_insider_trade_xml(xml_url)
            for t in filing_trades:
                t["filing_date"] = filing_date.strftime("%Y-%m-%d")
            trades.extend(filing_trades)

            sleep(1)
        except Exception as e:
            print(f"Error processing entry: {e}")
            continue

    return trades

def get_daily_trades(target_date: datetime, count: int = 100) -> list[dict]:
    """
    Pulls all Form 4 insider trades filed on a specific day across all companies.
    Returns a list of trade dicts.
    """
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count={count}&output=atom"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"❌ Failed to fetch global Atom feed: {res.status_code}")
        return []

    soup = BeautifulSoup(res.content, "xml")
    entries = soup.find_all("entry")
    all_trades = []
    # target_date = target_date.strftime("%Y-%m-%d")

    for entry in entries:
        try:
            filing_date = _get_filing_date_from_entry(entry)
            if filing_date != target_date:
                continue

            index_url = entry.find("link")["href"]
            xml_url = _get_primary_xml(index_url)
            if not xml_url:
                continue

            filing_trades = _parse_insider_trade_xml(xml_url)
            for t in filing_trades:
                t["filing_date"] = target_date
                t["filing_url"] = index_url

            all_trades.extend(filing_trades)
            sleep(1)

        except Exception as e:
            print(f"⚠️ Error parsing entry from global feed: {e}")
            continue

    if not all_trades:
        print(f"⚠️ No insider trades found for {target_date}")

    return all_trades

def _get_filing_date_from_entry(entry) -> date | None:
    try:
        updated_str = entry.find("updated").text[:10]
        return datetime.strptime(updated_str, "%Y-%m-%d").date()
    except:
        return None

def _get_primary_xml(index_url: str) -> str | None:
    """
    Given an index page URL for a Form 4 filing, return the direct link to the primary XML.
    """
    try:
        res = requests.get(index_url, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")

        tables = soup.find_all("table")
        for table in tables:
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    cell_text = cols[2].get_text(strip=True).lower()
                    if ".xml" in cell_text:
                        link_tag = cols[2].find("a")
                        if link_tag and link_tag.get("href"):
                            rel_url = link_tag["href"]
                            full_url = f"https://www.sec.gov{rel_url}"
                            sleep(1)  # SEC rate limit
                            return full_url

    except Exception as e:
        print(f"⚠️ Error while fetching XML link: {e}")

    print(f"⚠️ No XML link found on page: {index_url}")
    return None

def _parse_insider_trade_xml(xml_url: str) -> list[dict]:
    """
    Parses a Form 4 XML URL and extracts all reported insider transactions.
    Returns a list of trade dictionaries.
    """
    try:
        res = requests.get(xml_url, headers=HEADERS)
        soup = BeautifulSoup(res.content, "xml")

        # Get issuer info (ticker)
        ticker_tag = soup.find("issuerTradingSymbol")
        ticker = ticker_tag.text if ticker_tag else "UNKNOWN"

        # Get insider info
        owner_name = soup.find("rptOwnerName")
        officer_title = soup.find("officerTitle")
        owner_name = owner_name.text if owner_name else "Unknown"
        officer_title = officer_title.text if officer_title else "Unknown"

        trades = []

        for transaction in soup.find_all("nonDerivativeTransaction"):
            try:
                security = transaction.find("securityTitle").value.text
                code = transaction.find("transactionCode").text
                shares = float(safe_get_text(transaction.find("transactionShares"), "value", 0))
                price = float(safe_get_text(transaction.find("transactionPricePerShare"), "value", 0))
                total_value = round(shares * price, 2)

                trade = {
                    "ticker": ticker,
                    "insider_name": owner_name,
                    "title": officer_title,
                    "type": "Buy" if code == "P" else "Sell",
                    "security": security,
                    "shares": shares,
                    "price": price,
                    "value": total_value,
                    "code": code

                }

                trades.append(trade)

            except Exception as e:
                print(f"⚠️ Error parsing transaction: {e}")
                continue

        return trades

    except Exception as e:
        print(f"❌ Failed to parse XML at {xml_url}: {e}")
        return []
    
