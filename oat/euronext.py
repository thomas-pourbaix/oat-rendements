"""Récupération des obligations d'État françaises cotées sur Euronext Paris.

Source : l'API JSON qui alimente l'annuaire des obligations d'Euronext Live
(https://live.euronext.com/fr/products/fixed-income/paris/list).
"""

import re
import time
from dataclasses import dataclass
from datetime import date, datetime

import requests

URL = "https://live.euronext.com/fr/product_directory/data/bonds-paris?mics=ALXP%2CXMLI%2CXPAR"
USER_AGENT = "Mozilla/5.0 (compatible; oat-rendements; +https://github.com/thomas-pourbaix/oat-rendements)"
ISSUER = "REPUBLIC OF FRANCE"
PAGE_SIZE = 1000

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


@dataclass
class Quote:
    isin: str
    mic: str
    name: str
    maturity: date
    last_price: float          # prix pied de coupon, en % du nominal
    last_trade: datetime | None

    @property
    def url(self) -> str:
        return f"https://live.euronext.com/fr/product/bonds/{self.isin}-{self.mic}"


def _text(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _post(session: requests.Session, start: int) -> dict:
    last_error = None
    for attempt in range(6):
        try:
            r = session.post(URL, data={"sEcho": 1, "iDisplayStart": start, "iDisplayLength": PAGE_SIZE},
                             timeout=90)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:  # réponse vide intermittente
            last_error = e
            time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"Euronext injoignable (offset {start}) : {last_error}")


def fetch_rows() -> list[list[str]]:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    rows, start = [], 0
    while True:
        page = _post(session, start)
        rows += page["aaData"]
        start += PAGE_SIZE
        if not page["aaData"] or start >= int(page["iTotalRecords"]):
            return rows


def _parse_price(cell: str) -> float | None:
    m = re.search(r"(\d[\d\s]*,\d+|\d+)", _text(cell).replace(" ", ""))
    return float(m.group(1).replace(" ", "").replace(",", ".")) if m and "%" in _text(cell) else None


def _parse_trade(cell: str) -> datetime | None:
    # ex. "25 Sep 202617:23 CEST" (date et heure collées une fois le HTML retiré)
    m = re.match(r"(\d{2}) (\w{3}) (\d{4})(\d{2}):(\d{2})", _text(cell))
    if not m or m.group(2) not in _MONTHS:
        return None
    d, mon, y, hh, mm = m.groups()
    return datetime(int(y), _MONTHS[mon], int(d), int(hh), int(mm))


def parse(rows: list[list[str]]) -> list[Quote]:
    quotes = []
    for r in rows:
        if _text(r[1]) != ISSUER:
            continue
        link = re.search(r"bonds/([A-Z0-9]{12})-(\w+)", r[0])
        price = _parse_price(r[4])
        maturity = _text(r[3])
        if not link or price is None or not re.match(r"\d{4}-\d{2}-\d{2}$", maturity):
            continue
        quotes.append(Quote(
            isin=link.group(1),
            mic=link.group(2),
            name=_text(r[0]),
            maturity=date.fromisoformat(maturity),
            last_price=price,
            last_trade=_parse_trade(r[6]),
        ))
    return quotes


def fetch_french_govt_quotes() -> list[Quote]:
    return parse(fetch_rows())
