#!/usr/bin/env python3
"""Merge agent work fragments (work/*.json) into the source-of-truth JSON files.

A fragment lets parallel contributors work without editing the shared files:

  {
    "owner": "dit",                      # category key, or "arxiv-<batch>" for screening batches
    "models": [ {model record}, ... ],   # new or replacement records (matched by id)
    "figures": { "<id>": {figure record}, ... },
    "daily": [ {ledger row}, ... ]       # screened rows replacing pending rows (matched by arxiv_id)
  }

  python3 scripts/merge.py --check work/dit.json   # validate a fragment against the current catalog
  python3 scripts/merge.py work/*.json             # merge, then run scripts/catalog.py
"""

import argparse
import json
from pathlib import Path
import sys

from catalog import CATEGORIES, DAILY, DATA, FIGURES, ROOT, validate
from daily import validate_daily
from figures import validate_figures

SNAPSHOT_FIELDS = ("title", "listed_on", "paper_url")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def apply(fragments, catalog, manifest, ledger):
    seen_models, seen_rows = {}, {}
    rows = {r["arxiv_id"]: i for i, r in enumerate(ledger["records"])}
    models = {m["id"]: i for i, m in enumerate(catalog["models"])}
    report = []
    for path, frag in fragments:
        if set(frag) - {"owner", "models", "figures", "daily"} or not isinstance(frag.get("owner"), str):
            raise ValueError(f"{path}: fragment needs an owner and only models/figures/daily keys")
        owner = frag["owner"]
        added = replaced = 0
        for model in frag.get("models", []):
            mid = model["id"]
            if mid in seen_models:
                raise ValueError(f"{path}: model {mid} also appears in {seen_models[mid]}")
            seen_models[mid] = path
            if owner in CATEGORIES and model["category"] != owner:
                raise ValueError(f"{path}: {mid} is not in owner category {owner}")
            if mid in models:
                catalog["models"][models[mid]] = model
                replaced += 1
            else:
                models[mid] = len(catalog["models"])
                catalog["models"].append(model)
                added += 1
        for mid, figure in frag.get("figures", {}).items():
            manifest["models"][mid] = figure
        for row in frag.get("daily", []):
            aid = row["arxiv_id"]
            if aid in seen_rows:
                raise ValueError(f"{path}: arXiv {aid} also screened in {seen_rows[aid]}")
            seen_rows[aid] = path
            if aid not in rows:
                raise ValueError(f"{path}: arXiv {aid} is not in the pinned snapshot")
            current = ledger["records"][rows[aid]]
            if any(row.get(k) != current[k] for k in SNAPSHOT_FIELDS):
                raise ValueError(f"{path}: arXiv {aid} changes snapshot fields {SNAPSHOT_FIELDS}")
            ledger["records"][rows[aid]] = row
        report.append(f"{path}: {added} added, {replaced} replaced, {len(frag.get('figures', {}))} figures, {len(frag.get('daily', []))} screening rows")
    catalog["models"].sort(key=lambda m: m["id"])
    manifest["models"] = dict(sorted(manifest["models"].items()))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fragments", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate the merged result without writing")
    args = parser.parse_args()
    try:
        catalog, manifest, ledger = load(DATA), load(FIGURES), load(DAILY)
        report = apply([(str(p), load(p)) for p in args.fragments], catalog, manifest, ledger)
        validate(catalog)
        validate_figures(catalog, manifest, ROOT)
        pending = validate_daily(ledger, catalog, manifest["models"])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Merge error: {exc}", file=sys.stderr)
        return 1
    print("\n".join(report))
    if args.check:
        print(f"Fragment(s) valid against the current catalog; {pending} screening rows would remain pending.")
        return 0
    for path, data in ((DATA, catalog), (FIGURES, manifest), (DAILY, ledger)):
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Merged; {pending} screening rows pending. Now run: python3 scripts/catalog.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
