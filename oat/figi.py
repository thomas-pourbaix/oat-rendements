"""Caractéristiques des titres (coupon, type) via l'API publique OpenFIGI.

Pour une OAT, OpenFIGI renvoie un ticker du type « FRTR 3.25 02/25/32 OAT » :
coupon annuel 3,25 %, échéance, et suffixe indiquant la famille du titre.
Sans clé d'API : 10 ISIN par requête, 25 requêtes par minute.
"""

import re
import time

import requests

URL = "https://api.openfigi.com/v3/mapping"
BATCH = 10

# suffixe du ticker -> famille
KINDS = {"OAT": "nominale", "OATe": "indexee_euro", "OATi": "indexee_france"}


def _classify(ticker: str, name: str) -> str:
    if ticker.startswith("FRTRD") or "STRP" in name.upper():
        return "strip"
    return KINDS.get(ticker.split()[-1], "nominale")


def _describe(item: dict) -> dict | None:
    data = item.get("data") or []
    govt = [d for d in data if d.get("marketSector") == "Govt"] or data
    if not govt:
        return None
    d = next((x for x in govt if x.get("exchCode") == "EURONEXT-PARIS"), govt[0])
    ticker = d.get("ticker") or ""
    m = re.match(r"\S+ ([\d.]+) \d{2}/\d{2}/\d{2}", ticker)
    return {
        "ticker": ticker,
        "coupon": float(m.group(1)) if m else None,
        "kind": _classify(ticker, d.get("name") or ""),
    }


def describe(isins: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    session = requests.Session()
    for i in range(0, len(isins), BATCH):
        chunk = isins[i:i + BATCH]
        jobs = [{"idType": "ID_ISIN", "idValue": x} for x in chunk]
        for attempt in range(5):
            r = session.post(URL, json=jobs, timeout=60)
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            r.raise_for_status()
            break
        else:
            raise RuntimeError("OpenFIGI : limite de requêtes dépassée")
        for isin, item in zip(chunk, r.json()):
            desc = _describe(item)
            if desc:
                out[isin] = desc
        time.sleep(2.5)  # reste sous 25 requêtes / minute
    return out
