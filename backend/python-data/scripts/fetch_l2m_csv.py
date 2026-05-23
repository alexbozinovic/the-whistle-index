"""
Download and cache the atlhawksfanatic 2023-24 L2M CSV to data/l2m_2023_24.csv.
Run as a one-shot script; no-ops if the file already exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

L2M_URL = (
    "https://raw.githubusercontent.com/atlhawksfanatic/L2M"
    "/master/0-data/L2M/2023-24/scraped_202324.csv"
)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEST = DATA_DIR / "l2m_2023_24.csv"


def fetch() -> None:
    if DEST.exists():
        print(f"Already cached: {DEST}  ({DEST.stat().st_size:,} bytes)")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading L2M CSV from {L2M_URL} …")
    r = requests.get(L2M_URL, timeout=60)
    r.raise_for_status()
    DEST.write_bytes(r.content)
    print(f"Saved {len(r.content):,} bytes → {DEST}")


if __name__ == "__main__":
    fetch()
    sys.exit(0)
