"""
EDGAR lane (LIVE) — free, no key. domain/name -> CIK -> latest 10-K -> extract
Items 1/1A/7 -> Sonnet reduce to quoted, outreach-relevant facts.

Public/private branch: no CIK or no 10-K -> return NO_PUBLIC_FILING (a gap),
never a fabricated filing.
"""
import re
import warnings
from functools import lru_cache

import requests

from config import SEC_USER_AGENT
from llm import load_prompt, render, call_text

try:  # 10-K primary docs are XHTML; silence bs4's XML-as-HTML notice.
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except Exception:
    pass

_HEADERS = {"User-Agent": SEC_USER_AGENT}
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"

_ITEM_STARTS = {
    "Business": r"item\s*1\.",
    "Risk Factors": r"item\s*1a\.",
    "MD&A": r"item\s*7\.",
}
_ITEM_ENDS = {
    "Business": r"item\s*1a\.",
    "Risk Factors": r"item\s*1b\.",
    "MD&A": r"item\s*7a\.",
}


@lru_cache(maxsize=1)
def _tickers():
    r = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=30)
    r.raise_for_status()
    return list(r.json().values())  # {cik_str, ticker, title}


def resolve_cik(domain, company_name=None):
    label = (company_name or domain.split(".")[0]).lower().strip()
    if not label:
        return None
    for c in _tickers():
        title = c["title"].lower()
        if label == title.split()[0] or label in title:
            return str(c["cik_str"]).zfill(10), c["title"]
    return None


def _latest_10k(cik10):
    r = requests.get(_SUBMISSIONS_URL.format(cik10=cik10), headers=_HEADERS, timeout=30)
    r.raise_for_status()
    recent = r.json()["filings"]["recent"]
    for form, acc, doc, date in zip(
        recent["form"], recent["accessionNumber"],
        recent["primaryDocument"], recent["filingDate"],
    ):
        if form == "10-K":
            url = (f"https://www.sec.gov/Archives/edgar/data/"
                   f"{int(cik10)}/{acc.replace('-', '')}/{doc}")
            return url, date
    return None, None


def _to_text(html):
    try:
        from unstructured.partition.html import partition_html
        return "\n".join(e.text for e in partition_html(text=html) if e.text)
    except Exception:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for t in soup(["script", "style"]):
            t.extract()
        return soup.get_text("\n")


def _extract_items(text):
    """Best-effort slice of Items 1/1A/7. 10-Ks repeat 'Item 1.' in the TOC, so
    take the LAST occurrence of each start marker (the real section body)."""
    low = text.lower()
    out = []
    for name, start_pat in _ITEM_STARTS.items():
        starts = [m.end() for m in re.finditer(start_pat, low)]
        if not starts:
            continue
        s = starts[-1]
        ends = [m.start() for m in re.finditer(_ITEM_ENDS[name], low) if m.start() > s]
        e = ends[0] if ends else s + 6000
        chunk = text[s:e].strip()
        if len(chunk) > 200:
            out.append(f"=== {name} ===\n{chunk[:6000]}")
    return "\n\n".join(out) if out else text[:12000]


def run(domain, company_name=None):
    """Returns dict: {is_public, cik, name, text, url}. text feeds synthesis."""
    resolved = resolve_cik(domain, company_name)
    if not resolved:
        return {"is_public": False, "cik": None, "name": company_name,
                "text": "NO_PUBLIC_FILING", "url": None}
    cik10, title = resolved
    url, date = _latest_10k(cik10)
    if not url:
        return {"is_public": False, "cik": cik10, "name": title,
                "text": "NO_PUBLIC_FILING", "url": None}

    html = requests.get(url, headers=_HEADERS, timeout=60).text
    excerpt = _extract_items(_to_text(html))

    system, user_t = load_prompt("prompts/edgar_reduce.md")
    reduced = call_text(system, render(user_t, account_name=title,
                                       filing_url=url, filing_excerpt=excerpt))
    if "NO_USABLE_10K_CONTENT" in reduced:
        reduced = "NO_USABLE_10K_CONTENT"
    return {"is_public": True, "cik": cik10, "name": title,
            "text": f"10-K filing: {url} ({date})\n{reduced}", "url": url}
