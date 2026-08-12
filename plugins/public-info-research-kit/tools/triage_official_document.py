#!/usr/bin/env python3
"""Offline triage for official-source identity, HTML tables and PDF text layers.

This module performs no network access, login, OCR or external write. It only
classifies user-provided/local evidence so a later resolver can choose the
smallest safe next action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import string
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from pypdf import PdfReader


OFFICIAL_IDENTITY_STATES = {
    "official_confirmed",
    "official_candidate_needs_crosslink",
    "repost_or_aggregator",
    "identity_unresolved",
}
PDF_TRIAGE_STATES = {
    "native_text_ok",
    "mixed_page_partial_ocr",
    "scan_ocr_required",
    "human_spotcheck_required",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def classify_official_identity(evidence: dict[str, Any]) -> dict[str, Any]:
    """Classify identity from explicit evidence, never from URL appearance alone."""

    flags = {
        key: bool(evidence.get(key))
        for key in (
            "government_domain",
            "official_directory_link",
            "same_org_parent_link",
            "page_publisher_match",
            "canonical_crosslink",
            "document_identifier_match",
            "aggregator_only",
            "conflicting_publisher",
        )
    }
    if flags["aggregator_only"]:
        state = "repost_or_aggregator"
        score = 0
    else:
        weights = {
            "government_domain": 2,
            "official_directory_link": 2,
            "same_org_parent_link": 2,
            "page_publisher_match": 1,
            "canonical_crosslink": 2,
            "document_identifier_match": 1,
        }
        score = sum(weights[key] for key, value in flags.items() if value and key in weights)
        strong_link = (
            flags["official_directory_link"]
            or flags["same_org_parent_link"]
            or flags["canonical_crosslink"]
        )
        if score >= 4 and strong_link and not flags["conflicting_publisher"]:
            state = "official_confirmed"
        elif score >= 2 and not flags["conflicting_publisher"]:
            state = "official_candidate_needs_crosslink"
        else:
            state = "identity_unresolved"
    return {
        "state": state,
        "evidence_score": score,
        "evidence": flags,
        "rule": "search may discover a candidate; confirmation requires organization/domain/crosslink or document identity evidence",
    }


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[dict[str, Any]]]] = []
        self._depth = 0
        self._rows: list[list[dict[str, Any]]] = []
        self._row: list[dict[str, Any]] | None = None
        self._parts: list[str] | None = None
        self._attrs: dict[str, str] = {}
        self._tag = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag == "table":
            if self._depth == 0:
                self._rows = []
            self._depth += 1
        elif self._depth and tag == "tr":
            self._row = []
        elif self._depth and tag in {"td", "th"}:
            self._parts = []
            self._attrs = attrs_dict
            self._tag = tag

    def handle_data(self, data: str) -> None:
        if self._parts is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._depth and tag in {"td", "th"} and self._parts is not None:
            try:
                rowspan = max(1, int(self._attrs.get("rowspan") or "1"))
            except ValueError:
                rowspan = 1
            try:
                colspan = max(1, int(self._attrs.get("colspan") or "1"))
            except ValueError:
                colspan = 1
            if self._row is not None:
                self._row.append(
                    {
                        "text": compact("".join(self._parts)),
                        "rowspan": rowspan,
                        "colspan": colspan,
                        "tag": self._tag,
                    }
                )
            self._parts = None
            self._attrs = {}
            self._tag = ""
        elif self._depth and tag == "tr" and self._row is not None:
            if any(cell["text"] for cell in self._row):
                self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._depth:
            self._depth -= 1
            if self._depth == 0:
                self.tables.append(self._rows)
                self._rows = []


def _table_matrix(rows: list[list[dict[str, Any]]]) -> list[list[str]]:
    grid: list[list[str]] = []
    spans: dict[tuple[int, int], tuple[str, int]] = {}
    for row_index, row in enumerate(rows):
        output: list[str] = []
        column_index = 0

        def fill_spans() -> None:
            nonlocal column_index
            while (row_index, column_index) in spans:
                text, remaining = spans.pop((row_index, column_index))
                output.append(text)
                if remaining > 1:
                    spans[(row_index + 1, column_index)] = (text, remaining - 1)
                column_index += 1

        fill_spans()
        for cell in row:
            fill_spans()
            for _ in range(cell["colspan"]):
                output.append(cell["text"])
                if cell["rowspan"] > 1:
                    spans[(row_index + 1, column_index)] = (
                        cell["text"],
                        cell["rowspan"] - 1,
                    )
                column_index += 1
        fill_spans()
        if any(output):
            grid.append(output)
    return grid


def parse_html_tables(raw_html: str) -> list[list[list[str]]]:
    parser = _TableParser()
    parser.feed(raw_html)
    return [_table_matrix(rows) for rows in parser.tables]


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    acceptable = set(string.printable)
    good = sum(char in acceptable or "\u4e00" <= char <= "\u9fff" for char in text)
    return good / len(text)


def _page_image_coverage(page: Any) -> tuple[int, float]:
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    page_area = max(page_width * page_height, 1.0)
    max_pixel_area = 0
    image_count = 0
    try:
        for image_file in page.images:
            image_count += 1
            image = getattr(image_file, "image", None)
            if image is not None:
                width, height = image.size
                max_pixel_area = max(max_pixel_area, int(width) * int(height))
    except Exception:
        return image_count, 0.0
    return image_count, min(1.0, max_pixel_area / page_area)


def classify_pdf(path: Path) -> dict[str, Any]:
    reader = PdfReader(str(path))
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        compact_text = re.sub(r"\s+", "", text)
        char_count = len(compact_text)
        printable_ratio = _printable_ratio(compact_text)
        replacement_ratio = compact_text.count("\ufffd") / max(char_count, 1)
        image_count, image_coverage = _page_image_coverage(page)

        if char_count >= 80 and printable_ratio >= 0.85 and replacement_ratio <= 0.02:
            state = "native_text_ok"
        elif char_count < 20 and image_count and image_coverage >= 0.5:
            state = "scan_ocr_required"
        else:
            state = "human_spotcheck_required"
        pages.append(
            {
                "page": index,
                "state": state,
                "text_char_count": char_count,
                "printable_ratio": round(printable_ratio, 4),
                "replacement_ratio": round(replacement_ratio, 4),
                "image_count": image_count,
                "max_image_coverage_estimate": round(image_coverage, 4),
            }
        )

    states = {page["state"] for page in pages}
    if states == {"native_text_ok"}:
        document_state = "native_text_ok"
        ocr_pages: list[int] = []
    elif states == {"scan_ocr_required"}:
        document_state = "scan_ocr_required"
        ocr_pages = [page["page"] for page in pages]
    elif "scan_ocr_required" in states and "native_text_ok" in states:
        document_state = "mixed_page_partial_ocr"
        ocr_pages = [page["page"] for page in pages if page["state"] == "scan_ocr_required"]
    else:
        document_state = "human_spotcheck_required"
        ocr_pages = [page["page"] for page in pages if page["state"] == "scan_ocr_required"]

    return {
        "path": path.name,
        "source_sha256": sha256_file(path),
        "document_state": document_state,
        "page_count": len(pages),
        "ocr_pages": ocr_pages,
        "pages": pages,
        "boundary": "classification only; no OCR was executed and table reading order still needs field-level validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--identity-json", type=Path)
    args = parser.parse_args()
    if sum(value is not None for value in (args.pdf, args.html, args.identity_json)) != 1:
        parser.error("provide exactly one of --pdf, --html or --identity-json")

    if args.pdf:
        result: Any = classify_pdf(args.pdf)
    elif args.html:
        result = {"tables": parse_html_tables(args.html.read_text(encoding="utf-8"))}
    else:
        payload = json.loads(args.identity_json.read_text(encoding="utf-8"))
        result = [
            {**item, "classification": classify_official_identity(item.get("evidence", {}))}
            for item in payload
        ]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
