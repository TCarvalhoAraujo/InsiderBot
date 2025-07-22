import requests
from bs4 import BeautifulSoup

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