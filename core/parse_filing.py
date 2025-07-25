import requests
from bs4 import BeautifulSoup

from config.constants import HEADERS

def parse_insider_trade(xml_url: str) -> list[dict]:
    """
    Parses the XML Form 4 filing and extracts all insider trades.
    Returns a list of dictionaries with relevant data.
    """
    res = requests.get(xml_url, headers=HEADERS)
    soup = BeautifulSoup(res.content, "xml")

     # Get issuer ticker from the XML
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
            print(f"Error parsing transaction: {e}")
            continue

    return trades 

def safe_get_text(element, subtag=None, default=None):
    try:
        if subtag:
            return element.find(subtag).text if element.find(subtag) else default
        return element.text if element else default
    except:
        return default
