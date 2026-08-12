#!/usr/bin/env python3
"""Build a stable exact-query plan from a validated WeChat publisher list."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_wechat_account_list import canonical_sha256, normalized, validate_request


def build_plan(request: dict[str, Any]) -> dict[str, Any]:
    errors = validate_request(request)
    if errors:
        return {"schema": "wechat_exact_query_plan.v1", "status": "fail", "errors": errors, "queries": [], "platform_opened": False}

    strategy = request["query_strategy"]
    keywords: list[str] = []
    seen_keywords: set[str] = set()
    for keyword in strategy["keywords"]:
        key = normalized(keyword)
        if key not in seen_keywords:
            seen_keywords.add(key)
            keywords.append(" ".join(str(keyword).split()))

    queries: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for account in sorted(request["publisher_accounts"], key=lambda row: row["publisher_id"]):
        names = [account["display_name"]]
        if strategy["include_aliases"]:
            names.extend(account.get("aliases", []))
        for name in names:
            for keyword in keywords:
                exact_text = " ".join(f"{name} {keyword}".split())
                text_key = normalized(exact_text)
                if text_key in seen_text:
                    continue
                seen_text.add(text_key)
                digest = hashlib.sha256(f"{account['publisher_id']}\0{text_key}".encode("utf-8")).hexdigest()[:12]
                queries.append(
                    {
                        "query_id": f"wxq-{digest}",
                        "publisher_id": account["publisher_id"],
                        "publisher_name_used": name,
                        "exact_query_text": exact_text,
                    }
                )
    return {
        "schema": "wechat_exact_query_plan.v1",
        "status": "pass",
        "task_id": request["task_id"],
        "request_sha256": canonical_sha256(request),
        "query_count": len(queries),
        "queries": queries,
        "max_articles_per_publisher": strategy["max_articles_per_publisher"],
        "time_scope": strategy.get("time_scope"),
        "usage_boundary": request["usage_boundary"],
        "stop_condition": request["stop_condition"],
        "platform_opened": False,
        "network_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = build_plan(request)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
