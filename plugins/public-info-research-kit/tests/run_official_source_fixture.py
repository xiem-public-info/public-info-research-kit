#!/usr/bin/env python3
"""Offline official-identity and merged-header HTML fixtures without network access."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/triage_official_document.py"
SPEC = importlib.util.spec_from_file_location("triage_official_document", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> int:
    identity_cases = [
        (
            "official_confirmed",
            {"government_domain": True, "official_directory_link": True, "page_publisher_match": True},
            "official_confirmed",
        ),
        (
            "official_candidate_needs_crosslink",
            {"government_domain": True},
            "official_candidate_needs_crosslink",
        ),
        (
            "aggregator_is_not_official",
            {"aggregator_only": True, "page_publisher_match": True},
            "repost_or_aggregator",
        ),
        (
            "conflicting_publisher_is_unresolved",
            {"government_domain": True, "page_publisher_match": True, "conflicting_publisher": True},
            "identity_unresolved",
        ),
    ]
    cases = []
    for case_id, evidence, expected in identity_cases:
        actual = MODULE.classify_official_identity(evidence)["state"]
        cases.append({"case_id": case_id, "expected": expected, "actual": actual, "passed": actual == expected})

    html = """
    <table>
      <tr><th rowspan="2">事项编号</th><th colspan="2">结果信息</th></tr>
      <tr><th>结果日期</th><th>发布主体</th></tr>
      <tr><td>TEST-001</td><td>2026-09-01</td><td>示例部门</td></tr>
    </table>
    """
    matrix = MODULE.parse_html_tables(html)
    expected_matrix = [
        ["事项编号", "结果信息", "结果信息"],
        ["事项编号", "结果日期", "发布主体"],
        ["TEST-001", "2026-09-01", "示例部门"],
    ]
    cases.append(
        {
            "case_id": "merged_html_header_expands_deterministically",
            "expected": expected_matrix,
            "actual": matrix[0] if matrix else None,
            "passed": bool(matrix) and matrix[0] == expected_matrix,
        }
    )
    cases.append(
        {
            "case_id": "pdf_triage_states_are_explicit",
            "expected": ["human_spotcheck_required", "mixed_page_partial_ocr", "native_text_ok", "scan_ocr_required"],
            "actual": sorted(MODULE.PDF_TRIAGE_STATES),
            "passed": sorted(MODULE.PDF_TRIAGE_STATES) == ["human_spotcheck_required", "mixed_page_partial_ocr", "native_text_ok", "scan_ocr_required"],
        }
    )

    report = {
        "schema": "official_source_fixture_report.v1",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "pdf_boundary": "PDF runtime classification is retained; this dependency-light fixture covers identity, table structure and explicit PDF states",
        "network_accessed": False,
        "ocr_executed": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
