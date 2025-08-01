import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def finviz_scraper():
    url = "https://finviz.com/insidertrading.ashx?tc=1" #1tc=1 filters only buys
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", id="insider-table")
    rows = table.find_all("tr")[1:]  # Skip header

    data = []

    for row in rows:
        cols = [col.text.strip() for col in row.find_all("td")]
        if not cols or len(cols) < 10:
            continue

        trade = {
            "ticker": cols[0],
            "insider_name": cols[1],
            "relationship": cols[2],
            "transaction_date": datetime.strptime(cols[3], "%b %d '%y").replace(year=datetime.today().year),
            "transaction_type": cols[4],
            "price": float(cols[5].replace("$", "").replace(",", "")) if cols[5] else None,
            "shares": int(cols[6].replace(",", "")) if cols[6] else None,
            "value": cols[7],
            "shares_total": cols[8],
            "sec_form4": "https://finviz.com/" + row.find_all("td")[9].find("a")["href"],
        }

        data.append(trade)

    df = pd.DataFrame(data)
    return df
