import requests
from bs4 import BeautifulSoup
import time

from config.constants import HEADERS

def get_primary_xml(index_url: str) -> str | None:
    """
    Given a filing index page, return the full XML URL if it exists.
    """
    try:
        res = requests.get(index_url, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")

        tables = soup.find_all("table")
        for table in tables:
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    text = cols[2].get_text(strip=True).lower()
                    if ".xml" in text:
                        link_tag = cols[2].find("a")
                        if link_tag and link_tag.get("href"):
                            rel_url = link_tag["href"]
                            full_url = f"https://www.sec.gov{rel_url}"
                            time.sleep(1)  ## Delay required for making 10 requests per second
                            return full_url

    except Exception as e:
        print(f"Error while fetching XML link: {e}")

    print(f"No XML link found on page: {index_url}")
    return None