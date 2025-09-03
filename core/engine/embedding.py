import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

from transformers import pipeline
from tqdm import tqdm

def fetch_filing_html(url: str) -> str:
    """Fetch raw SEC filing HTML text given a URL."""
    url = url.replace("http://", "https://")
    if "finviz.com/" in url:
        url = url.split("finviz.com/")[-1]

    resp = requests.get(
        url,
        headers={"User-Agent": "InsiderBot - CaseStudy (thicoaraujo1@gmail.com)",
                 "Accept-Encoding": "gzip, deflate",
                 "Host": "www.sec.gov"})
    resp.raise_for_status()
    return resp.text

def extract_footnotes(html: str) -> list[str]:
    """Extract footnotes from SEC filing (XML <footnote> or Explanation of Responses)."""
    soup = BeautifulSoup(html, "lxml")

    # XML <footnote>
    footnotes = [fn.get_text(strip=True) for fn in soup.find_all("footnote")]
    if footnotes:
        return footnotes

    # Fallback: Explanation of Responses
    text = soup.get_text("\n")
    match = re.search(
        r"Explanation of Responses:(.*?)(Remarks:|\*\* Signature of Reporting Person|Reminder:|$)",
        text,
        re.S
    )
    if not match:
        return []

    block = match.group(1).strip()
    numbered = re.findall(r"(\d+\..*?)(?=\n\d+\.|\Z)", block, re.S)
    return [fn.strip().replace("\n", " ") for fn in numbered]


def classify_footnotes(footnotes: list[str], classifier=None) -> tuple[list[str], list[str]]:
    """
    Map footnotes into tags & notes.
    - Uses rules first (DRIP, 10b5-1, options, disclaimers, etc.)
    - Falls back to embeddings if classifier is provided
    - Default = Conviction Buy
    """
    tags, notes = [], []

    for fn in footnotes:
        text = fn.lower()

        # --- 📥 AUTOMATIC / SCHEDULED ---
        if "dividend reinvestment" in text:
            tags.append("Automatic/Scheduled")
            notes.append("Dividend Reinvestment Plan → automatic buy.")
            continue
        if "10b5-1" in text:
            tags.append("Automatic/Scheduled")
            notes.append("10b5-1 prearranged plan.")
            continue

        # --- 🎁 COMPENSATION / ACCOUNTING ---
        if "option" in text and "exercise" in text:
            tags.append("Compensation/Accounting")
            notes.append("Option exercise, not pure conviction.")
            continue
        if "grant" in text or "award" in text:
            tags.append("Compensation/Accounting")
            notes.append("Stock grant/award.")
            continue
        if "equity compensation" in text or "debt conversion" in text:
            tags.append("Compensation/Accounting")
            notes.append("Equity comp / debt conversion, non-cash.")
            continue

        # --- ⚖️ OWNERSHIP DISCLAIMER / INDIRECT ---
        if "disclaims beneficial ownership" in text or "may be deemed to beneficially own" in text:
            tags.append("Ownership Disclaimer/Indirect")
            notes.append("Beneficial ownership disclaimer or indirect fund/trust structure.")
            continue
        if "held for the account of" in text or "serves as general partner" in text:
            tags.append("Ownership Disclaimer/Indirect")
            notes.append("Indirect ownership via funds, LP/LLC, or trusts.")
            continue

        # --- ✅ CONVICTION BUY ---
        if "weighted average" in text or "multiple transactions" in text:
            tags.append("Conviction Buy")
            notes.append("Weighted average / multiple transactions → open-market conviction.")
            continue
        if "401(k)" in text:
            tags.append("Conviction Buy")
            notes.append("401(k) purchases treated as conviction buy (employee-directed contributions).")
            continue

        # --- FALLBACK: EMBEDDING MODEL ---
        #if classifier:
        #    candidate_labels = [
        #        "Automatic/Scheduled",
        #        "Compensation/Accounting",
        #        "Ownership Disclaimer/Indirect",
        #        "Conviction Buy"
        #    ]
        #    result = classifier(fn, candidate_labels, multi_label=False)
        #    pred = result["labels"][0]
        #    tags.append(pred)
        #    notes.append(f"Embedding model classified as {pred}.")
        #else:
        #    tags.append("Conviction Buy")
        #    notes.append("No matching rule → defaulted to conviction.")

    if not tags:
        tags.append("Conviction Buy")
        notes.append("No footnotes detected → treated as conviction buy.")

    return tags, notes

def update_motive_tags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Iterate through trades in dataframe, fetch filings, extract footnotes,
    classify into tags, and return updated dataframe.
    """
    all_tags, all_notes = [], []

    # classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    # tqdm wraps the iterator so you see a progress bar
    for _, row in tqdm(df.iterrows(), total=len(df), desc="🔍 Updating motive tags"):
        try:
            html = fetch_filing_html(row["sec_form4"])
            footnotes = extract_footnotes(html)
            tags, notes = classify_footnotes(footnotes, ) # classifier
        except Exception as e:
            tags, notes = ["❌ Error"], [str(e)]

        all_tags.append(tags)
        all_notes.append(notes)

    df["footnote_tags"] = all_tags
    df["footnote_notes"] = all_notes
    return df
