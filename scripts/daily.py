"""Validate and render the pinned 2025+ arXiv text-to-image screening record, offline.

Adapted from kadirnar/awesome-tts-architectures (Apache-2.0). The discovery source is a pinned
arXiv API snapshot (see scripts/fetch_arxiv.py) instead of a third-party daily list.
"""

from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
import re
from urllib.parse import urlsplit


REASONS = {
    "distinct-t2i-system": "Text-to-image model, generation architecture or named generation system",
    "data-or-evaluation": "Dataset, benchmark, evaluation or analysis without a distinct text-to-image system",
    "component-or-training-method": "Component, guidance, control, personalization, editing, safety, acceleration or training method without a distinct generation system",
    "outside-t2i": "Image understanding, retrieval, video, 3D or application outside the text-to-image scope",
    "no-distinct-t2i-system": "No distinct text-to-image system identified in the reviewed source",
    "before-2025": "First paper submission predates January 1, 2025",
}
API = "https://export.arxiv.org/api/query"


def snapshot_digest(records):
    """Checksum of the snapshot rows, independent of screening decisions."""
    rows = sorted((r["arxiv_id"], r["title"], r["listed_on"]) for r in records)
    return sha256("\n".join("\t".join(row) for row in rows).encode("utf-8")).hexdigest()


def validate_daily(ledger, catalog, figures):
    """Validate the ledger and return the number of rows still pending screening."""
    if ledger.get("schema_version") != 1:
        raise ValueError("Unsupported daily screening schema")
    source = ledger["source"]
    if source["api"] != API or not source["search_query"].strip():
        raise ValueError("Daily source must record the arXiv API query")
    if not re.fullmatch(r"[0-9a-f]{64}", source["snapshot_sha256"]):
        raise ValueError("Daily source requires a snapshot checksum")
    start = date.fromisoformat(ledger["min_first_submission_date"])
    retrieved = date.fromisoformat(source["retrieved_on"])
    reviewed = date.fromisoformat(ledger["reviewed_on"])
    if start != date(2025, 1, 1) or retrieved > reviewed or reviewed > date.fromisoformat(catalog["as_of"]):
        raise ValueError("Invalid daily review dates")
    records = ledger["records"]
    if len(records) != ledger["eligible_row_count"] or len(records) != ledger["source_row_count"]:
        raise ValueError("Daily screening row count does not match the snapshot")
    if snapshot_digest(records) != source["snapshot_sha256"]:
        raise ValueError("Daily screening rows do not match the snapshot checksum")
    models = {m["id"]: m for m in catalog["models"]}
    seen = set()
    pending = 0
    for row in records:
        aid = row["arxiv_id"]
        if not re.fullmatch(r"\d{4}\.\d{4,5}", aid) or aid in seen:
            raise ValueError(f"Daily record has an invalid or repeated paper: {aid}")
        seen.add(aid)
        if not row["title"].strip() or row["paper_url"] != f"https://arxiv.org/abs/{aid}":
            raise ValueError(f"{aid}: invalid daily paper metadata")
        if date.fromisoformat(row["listed_on"]) > retrieved:
            raise ValueError(f"{aid}: listed date after the snapshot")
        if row["decision"] == "pending":
            if set(row) != {"arxiv_id", "title", "listed_on", "paper_url", "review_level", "decision"} or row["review_level"] != "title":
                raise ValueError(f"{aid}: pending rows carry snapshot fields only")
            pending += 1
            continue
        if row["review_level"] not in {"title", "abstract", "paper"} or row["reason"] not in REASONS:
            raise ValueError(f"{aid}: unknown screening evidence or reason")
        if row["decision"] == "excluded":
            if row["reason"] == "distinct-t2i-system" or "model_id" in row:
                raise ValueError(f"{aid}: inconsistent exclusion")
            if row["reason"] == "before-2025" and date.fromisoformat(row.get("first_submitted", "9999-12-31")) >= start:
                raise ValueError(f"{aid}: before-2025 exclusion needs an earlier first_submitted date")
            continue
        if row["decision"] != "included" or row["reason"] != "distinct-t2i-system":
            raise ValueError(f"{aid}: invalid screening decision")
        if row["review_level"] == "title" or row["catalog_action"] not in {"added", "existing"}:
            raise ValueError(f"{aid}: included systems need primary-source review")
        first = date.fromisoformat(row["first_submitted"])
        if not start <= first <= reviewed:
            raise ValueError(f"{aid}: first submission outside the requested date window")
        mid = row["model_id"]
        if mid not in models or mid not in figures:
            raise ValueError(f"{aid}: missing model or image")
        model = models[mid]
        if not model.get("description") or "github_status" not in model:
            raise ValueError(f"{mid}: daily models need a description and GitHub review status")
        if row["catalog_action"] == "added" and (not model["source_date"] or date.fromisoformat(model["source_date"]) < start):
            raise ValueError(f"{mid}: new imports must be from 2025 onward")
        paper_urls = {s["url"] for s in model["sources"] if s["kind"] == "paper"}
        if row["paper_url"] not in paper_urls:
            raise ValueError(f"{mid}: screened paper missing from model sources")
        for evidence in row.get("repository_evidence", []):
            if evidence["url"] not in {s["url"] for s in model["sources"] if s["kind"] == "repository"}:
                raise ValueError(f"{mid}: repository evidence does not match the card")
            parsed = urlsplit(evidence["evidence_url"])
            if parsed.scheme != "https" or not parsed.netloc or evidence["verification"] not in {"paper-link", "project-link", "readme-paper-link", "readme-paper-match", "existing-reviewed-source"}:
                raise ValueError(f"{mid}: invalid repository verification evidence")
    return pending


def render_daily(ledger, catalog, figures, model_link, source_links):
    by_model = defaultdict(list)
    excluded = Counter()
    pending = 0
    for row in ledger["records"]:
        if row["decision"] == "included":
            by_model[row["model_id"]].append(row)
        elif row["decision"] == "pending":
            pending += 1
        else:
            excluded[row["reason"]] += 1
    models = [m for m in catalog["models"] if m["id"] in by_model]
    models.sort(key=lambda m: (min(r["first_submitted"] for r in by_model[m["id"]]), m["name"].casefold()), reverse=True)
    added = sum(any(r["catalog_action"] == "added" for r in by_model[m["id"]]) for m in models)
    github = sum(m["github_status"] == "author-linked" for m in models)
    primary_figures = sum(figures[m["id"]]["kind"] == "source-figure" for m in models)
    included_papers = sum(len(rows) for rows in by_model.values())
    source = ledger["source"]
    lines = [
        "# arXiv text-to-image papers · Models from 2025 onward", "",
        "<!-- Generated by scripts/catalog.py from data/t2i-arxiv-daily.json, data/models.json and data/figures.json. -->", "",
        "[← Complete catalog](../README.md#models)", "",
        f'**{len(models)} model families · {included_papers} papers · {added} new catalog entries · Reviewed {ledger["reviewed_on"]}**', "",
        f'Screens all **{ledger["eligible_row_count"]} papers** returned by the pinned arXiv API query `{source["search_query"]}`, retrieved on {source["retrieved_on"]} (snapshot SHA-256 `{source["snapshot_sha256"][:12]}…`). Inclusion requires a text-to-image model, distinct generation architecture or named generation system whose paper was first submitted on or after **January 1, 2025**. A later revision of a 2024 paper does not qualify. Earlier entries and releases without an arXiv paper are covered by the complete catalog.', "",
        "Datasets, benchmarks, guidance and control methods, personalization, editing-only methods, safety and concept erasure, acceleration techniques and methods without a distinct generation system are excluded. Closely related releases and renamed papers share a card. Descriptive names are used when a paper does not give its system a brand name.", "",
        f'Every family below has a description, a local image and paper links. **{github}** have author-linked GitHub sources; **{len(models) - github}** have no author-linked repository found in the reviewed sources. A missing link is a review result, not a claim that no repository exists. **{primary_figures}** images come from primary sources; **{len(models) - primary_figures}** are labeled editorial input/output diagrams.', "",
        "Dates are first paper submission dates, not verified software release dates. Withdrawals and renamed papers are noted on the affected cards. [Full screening and repository evidence](../data/t2i-arxiv-daily.json) · [Figure credits](../assets/architectures/CREDITS.md).", "",
        "<details>", "<summary>Screening counts</summary>", "",
        "| Decision | Papers |", "| --- | ---: |", f"| Included | {included_papers} |",
    ]
    lines += [f"| {REASONS[reason]} | {count} |" for reason, count in sorted(excluded.items())]
    if pending:
        lines.append(f"| Not yet screened | {pending} |")
    lines += ["", "</details>", "", "<details>", "<summary>Model index</summary>", ""]
    lines += [f'- [{m["name"]}](#{m["id"]})' for m in models]
    lines += ["", "</details>", "", "## Models", ""]
    if not models:
        lines += ["No screened models yet.", ""]
    for model in models:
        mid = model["id"]
        figure = figures[mid]
        first = min(r["first_submitted"] for r in by_model[mid])
        visual = "Editorial input/output diagram" if figure["kind"] == "io-diagram" else figure["locator"]
        lines += [
            f'<a id="{mid}"></a>', "", f'### {model["name"]}', "",
            f'**First paper submission:** {first} · [Architecture card]({model_link(model, "../")})', "",
            model["description"], "", source_links(model), "",
            f'![{model["name"]} — {visual}](../{figure["path"]})', "",
            f'*{visual} · [Image source]({figure["source_url"]})*', "",
        ]
    return "\n".join(lines).rstrip() + "\n"
