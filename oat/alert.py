# Copyright (C) 2026 Thomas Pourbaix
# SPDX-License-Identifier: AGPL-3.0-only

"""Email the owner when a watched bond's last price reaches a threshold.

Usage: python -m oat.alert [--data site/data/oats.json]

Configuration comes from environment variables (GitHub secrets in CI), never from the repository:
ALERT_ISIN, ALERT_THRESHOLD (price in %, e.g. 98), SMTP_USER, SMTP_PASSWORD (Gmail app password),
ALERT_EMAIL (recipient, defaults to SMTP_USER). The repository and its job logs are public, so this
script never prints the watched ISIN, the threshold, the price or an address.
"""

import argparse
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
CONFIG_KEYS = ("ALERT_ISIN", "ALERT_THRESHOLD", "SMTP_USER", "SMTP_PASSWORD")


class WatchedBondMissing(Exception):
    """The watched ISIN is not in the data: an alert that can never fire must not stay silent."""


def triggered(bonds: list[dict], isin: str, threshold: float) -> dict | None:
    """Return the watched bond if its last price is at or above the threshold, else None."""
    bond = next((b for b in bonds if b.get("isin") == isin), None)
    if bond is None:
        raise WatchedBondMissing
    price = bond.get("price")
    return bond if price is not None and price >= threshold else None


def message(bond: dict, threshold: float, sender: str, recipient: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = f"Alerte OAT : {bond['name']} à {bond['price']:.2f} % (seuil {threshold:g} %)"
    last_trade = (bond.get("last_trade") or "inconnue")[:10]
    msg.set_content(
        f"Le titre {bond['name']} ({bond['isin']}, échéance {bond['maturity']}) "
        f"a coté {bond['price']:.2f} % au dernier échange ({last_trade}).\n"
        f"Seuil d'alerte : {threshold:g} %.\n\n"
        f"Fiche Euronext : {bond['url']}\n\n"
        "Cours de clôture, avec quelques heures de retard. Vérifie le cours avant de passer un ordre, "
        "à tête reposée. Ce mail revient chaque soir tant que le seuil est atteint.\n"
    )
    return msg


def main(argv: list[str] | None = None, smtp_factory=smtplib.SMTP_SSL) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="site/data/oats.json")
    args = parser.parse_args(argv)

    if not all(os.environ.get(k) for k in CONFIG_KEYS):
        print("Price alert not configured, skipped.")
        return 0
    isin = os.environ["ALERT_ISIN"].strip()
    threshold = float(os.environ["ALERT_THRESHOLD"].replace(",", "."))
    sender = os.environ["SMTP_USER"].strip()
    recipient = (os.environ.get("ALERT_EMAIL") or sender).strip()

    bonds = json.loads(Path(args.data).read_text(encoding="utf-8"))["bonds"]
    try:
        bond = triggered(bonds, isin, threshold)
    except WatchedBondMissing:
        print("Price alert: the watched bond is missing from the data.", file=sys.stderr)
        return 1
    if bond is None:
        print("Price alert checked: not triggered.")
        return 0
    with smtp_factory(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(sender, os.environ["SMTP_PASSWORD"])
        smtp.send_message(message(bond, threshold, sender, recipient))
    print("Price alert checked: email sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
