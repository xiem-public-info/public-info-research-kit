#!/usr/bin/env python3
"""Validate and optionally sanitize XHS evidence-package pointers.

The checker is local only.  It never opens XHS or a browser.  Findings expose
JSON paths and blocked marker names, never the corresponding values.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BLOCKED_FIELD_NAMES = {
    "authorization",
    "authorization_header",
    "cookie",
    "cookie_header",
    "cookies",
    "storage_state",
    "local_storage",
    "request_header",
    "request_headers",
    "temporary_request_header",
    "temporary_request_headers",
    "xsec_token",
    "xsec_source",
    "access_token",
    "refresh_token",
    "id_token",
    "profile_path",
    "browser_profile",
    "browser_profile_path",
    "runtime_profile",
    "user_data_dir",
    "qr_credential",
    "qr_login_token",
    "scan_credential",
    "clipboard_content",
}
BLOCKED_QUERY_NAMES = {
    "xsec_token",
    "xsec_source",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "cookie",
    "storage_state",
    "local_storage",
}

BLOCKED_PROFILE_PATH_MARKERS = (
    "/library/application support/google/chrome/",
    "/library/application support/chromium/",
    "/browser_profile/",
    "/browser_data/",
    "/user_data_dir/",
    "/cdp_xhs_user_data_dir/",
    "/google/chrome/user data/",
)


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def is_blocked_profile_path(value: str) -> bool:
    normalized = value.strip().lower().replace("\\", "/")
    padded = f"/{normalized.strip('/')}/"
    return any(marker in padded for marker in BLOCKED_PROFILE_PATH_MARKERS)


def blocked_query_names(value: str) -> list[str]:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return []
    if not parsed.scheme or not parsed.netloc:
        return []
    return sorted({normalized_name(key) for key, _ in parse_qsl(parsed.query, keep_blank_values=True)} & BLOCKED_QUERY_NAMES)


def canonicalize_pointer(value: str) -> str:
    """Remove transient/security query parameters while preserving a stable URL."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value
    safe_query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if normalized_name(key) not in BLOCKED_QUERY_NAMES
    ]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(safe_query, doseq=True), parsed.fragment))


def validate(value: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def walk(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                marker = normalized_name(key)
                child_path = f"{path}.{key}"
                if marker in BLOCKED_FIELD_NAMES:
                    issues.append({"code": "blocked_sensitive_or_transient_field", "path": child_path, "marker": marker})
                else:
                    walk(child, child_path)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")
        elif isinstance(item, str):
            for marker in blocked_query_names(item):
                issues.append({"code": "blocked_sensitive_or_transient_url_parameter", "path": path, "marker": marker})
            if is_blocked_profile_path(item):
                issues.append({"code": "blocked_browser_profile_path", "path": path, "marker": "browser_profile_path"})

    walk(value, "$")
    return {
        "schema": "xhs_evidence_package_security_validation.v1",
        "status": "pass" if not issues else "fail",
        "passed": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "values_exposed": False,
        "platform_opened": False,
        "external_write_executed": False,
    }


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize(child)
            for key, child in value.items()
            if normalized_name(key) not in BLOCKED_FIELD_NAMES
        }
    if isinstance(value, list):
        return [sanitize(child) for child in value]
    if isinstance(value, str):
        if is_blocked_profile_path(value):
            return None
        return canonicalize_pointer(value)
    return copy.deepcopy(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sanitized-output", type=Path)
    parser.add_argument("--validation-output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    input_validation = validate(payload)
    result: dict[str, Any] = {"input_validation": input_validation}

    exit_passed = input_validation["passed"]
    if args.sanitized_output:
        sanitized = sanitize(payload)
        args.sanitized_output.parent.mkdir(parents=True, exist_ok=True)
        args.sanitized_output.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sanitized_validation = validate(sanitized)
        result["sanitized_validation"] = sanitized_validation
        result["sanitized_output"] = str(args.sanitized_output)
        exit_passed = sanitized_validation["passed"]

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.validation_output:
        args.validation_output.parent.mkdir(parents=True, exist_ok=True)
        args.validation_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if exit_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
