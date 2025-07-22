import requests
from bs4 import BeautifulSoup
import time

def get_primary_xml (index_url: str) -> str | None:
    """
    Given a filing index page, return the full XML URL if it exists.
    """

    headers = {
        "User-Agent": "InsiderBot - CaseStudy (thicoaraujo1@gmail.com)"
    }

    try:
        res = requests.get(index_url, headers=headers)
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
                            time.sleep(0.5)  ## Delay required for making 10 requests per second
                            return full_url

    except Exception as e:
        print(f"❌ Error while fetching XML link: {e}")

    print(f"⚠️ No XML link found on page: {index_url}")
    return None

## Downloading Atom Feed
url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=100&output=atom" ## Gets 100 latests filings
headers = {
    "User-Agent": "InsiderBot - CaseStudy (thicoaraujo1@gmail.com)"
}
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, "xml") ## Parse to xml format

## Parse each filing
entries = soup.find_all("entry")
for entry in entries:
    title = entry.find("title").text
    link = entry.find("link")["href"]
    print(f"{title}\n{link}\n")

## Testing
test_index_url = "https://www.sec.gov/Archives/edgar/data/1845014/000143510925000217/0001435109-25-000217-index.htm"
xml_url = get_primary_xml(test_index_url)

if xml_url:
    print(f"Found XML link:\n{xml_url}")
else:
    print("❌ Could not find XML link.")
