"""Stocks, indices and funds matching a name or ticker, from Yahoo Finance's search."""

import urllib.parse

from .. import net

SEARCH = "https://query1.finance.yahoo.com/v1/finance/search"
KINDS = ("EQUITY", "ETF", "INDEX", "MUTUALFUND", "CRYPTOCURRENCY")


def search(query, fetch=net.get_json):
    """[{"symbol", "name", "exchange", "type"}]; raises OSError/ValueError when offline."""
    q = (query or "").strip()[:40]
    if not q:
        return []
    url = f"{SEARCH}?{urllib.parse.urlencode({'q': q, 'quotesCount': 8, 'newsCount': 0})}"
    quotes = fetch(url).get("quotes") or []
    return [
        {
            "symbol": r["symbol"],
            "name": r.get("shortname") or r.get("longname") or "",
            "exchange": r.get("exchDisp") or r.get("exchange") or "",
            "type": (r.get("quoteType") or "").lower(),
        }
        for r in quotes
        if r.get("symbol") and r.get("quoteType") in KINDS
    ]
