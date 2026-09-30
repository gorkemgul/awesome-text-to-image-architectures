#!/usr/bin/env python3
"""Fetch the pinned arXiv text-to-image snapshot (abstract mentions "text-to-image", or title mentions image generation/synthesis) into data/t2i-arxiv-daily.json.

New papers are added as `pending` rows; existing screening decisions are kept. Rows that no
longer appear in the query are kept too, so a refresh never silently drops reviewed papers.
Uses only the standard library and respects arXiv's request pacing.
"""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from daily import API, snapshot_digest
from net import get

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "t2i-arxiv-daily.json"
ATOM = {"a": "http://www.w3.org/2005/Atom", "os": "http://a9.com/-/spec/opensearch/1.1/"}
PAGE = 200


def query_for(until):
    terms = 'abs:"text-to-image" OR ti:"image generation" OR ti:"image synthesis"'
    return f'({terms}) AND submittedDate:[202501010000 TO {until:%Y%m%d}2359]'


def fetch(search_query):
    rows, start, total = {}, 0, None
    while total is None or start < total:
        url = API + "?" + urlencode({"search_query": search_query, "start": start, "max_results": PAGE, "sortBy": "submittedDate", "sortOrder": "descending"})
        for attempt in range(5):
            feed = ET.fromstring(get(url)[1])
            entries = feed.findall("a:entry", ATOM)
            total = int(feed.findtext("os:totalResults", namespaces=ATOM))
            if entries or start >= total:
                break
            time.sleep(5 * (attempt + 1))  # arXiv occasionally returns an empty page; retry
        else:
            raise RuntimeError(f"arXiv returned no entries at offset {start} of {total}")
        for entry in entries:
            aid = re.sub(r"v\d+$", "", entry.findtext("a:id", namespaces=ATOM).rsplit("/abs/", 1)[1])
            rows[aid] = {
                "arxiv_id": aid,
                "title": " ".join(entry.findtext("a:title", namespaces=ATOM).split()),
                "listed_on": entry.findtext("a:published", namespaces=ATOM)[:10],
                "paper_url": f"https://arxiv.org/abs/{aid}",
                "review_level": "title",
                "decision": "pending",
            }
        start += PAGE
        print(f"fetched {min(start, total)}/{total}", file=sys.stderr)
        time.sleep(3)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--until", type=date.fromisoformat, default=date.today(), help="Last submission date to include (default: today)")
    args = parser.parse_args()
    search_query = query_for(args.until)
    fetched = fetch(search_query)
    if LEDGER.exists():
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    else:
        ledger = {"schema_version": 1, "source": {}, "reviewed_on": args.until.isoformat(), "min_first_submission_date": "2025-01-01", "records": []}
    existing = {r["arxiv_id"]: r for r in ledger["records"]}
    added = [aid for aid in fetched if aid not in existing]
    records = list(existing.values()) + [fetched[aid] for aid in added]
    records.sort(key=lambda r: (r["listed_on"], r["arxiv_id"]), reverse=True)
    ledger["source"] = {"api": API, "search_query": search_query, "retrieved_on": args.until.isoformat(), "snapshot_sha256": snapshot_digest(records)}
    ledger["reviewed_on"] = max(ledger["reviewed_on"], args.until.isoformat())
    ledger["source_row_count"] = ledger["eligible_row_count"] = len(records)
    ledger["records"] = records
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(fetched)} papers in query; {len(added)} new pending rows; {len(records)} rows in ledger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
