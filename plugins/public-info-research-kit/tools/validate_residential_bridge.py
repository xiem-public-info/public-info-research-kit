#!/usr/bin/env python3
"""Validate the public/residential v0.2 lock, optionally against a consumer checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "bridges/residential-v0.2/consumer-contract-lock.v0.2.json"
EXPECTED_CONSUMER_IDS = {
    "residential.upstream_task.v0.2",
    "residential.upstream_response.v0.2",
    "residential.upstream_adoption_receipt.v0.2",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(lock: dict[str, Any], consumer_root: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    if lock.get("schema") != "public.residential_bridge_lock.v0.2":
        errors.append("bridge lock schema is invalid")
    if lock.get("status") != "compatible_candidate_frozen":
        errors.append("bridge lock status is invalid")

    producer = lock.get("producer")
    if not isinstance(producer, dict):
        errors.append("producer lock is required")
        producer = {}
    producer_path = producer.get("schema_path")
    target = ROOT / producer_path if isinstance(producer_path, str) else None
    if not target or not target.is_file():
        errors.append("producer schema path is invalid")
    else:
        schema = json.loads(target.read_text(encoding="utf-8"))
        if schema.get("$id") != producer.get("$id") or producer.get("$id") != "public_evidence_envelope.v1":
            errors.append("producer schema id mismatch")
        if sha256_file(target) != producer.get("sha256"):
            errors.append("producer schema hash mismatch")

    consumer = lock.get("consumer")
    if not isinstance(consumer, dict):
        errors.append("consumer lock is required")
        consumer = {}
    commit = consumer.get("candidate_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("consumer candidate commit is invalid")
    contracts = consumer.get("contracts")
    if not isinstance(contracts, list) or len(contracts) != 3:
        errors.append("consumer contracts must contain three entries")
        contracts = []
    observed_ids: set[str] = set()
    external_checks: list[dict[str, Any]] = []
    for index, contract in enumerate(contracts):
        if not isinstance(contract, dict):
            errors.append(f"consumer contract {index} is invalid")
            continue
        relative = contract.get("path")
        schema_id = contract.get("$id")
        digest = contract.get("sha256")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            errors.append(f"consumer contract {index} path must be relative")
        if not isinstance(schema_id, str) or schema_id in observed_ids:
            errors.append(f"consumer contract {index} id is invalid or duplicated")
        else:
            observed_ids.add(schema_id)
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"consumer contract {index} hash is invalid")
        if consumer_root is not None and isinstance(relative, str) and not Path(relative).is_absolute():
            path = consumer_root / relative
            check = {"path": relative, "exists": path.is_file(), "id_matches": False, "hash_matches": False}
            if path.is_file():
                actual = json.loads(path.read_text(encoding="utf-8"))
                check["id_matches"] = actual.get("$id") == schema_id
                check["hash_matches"] = sha256_file(path) == digest
                if not check["id_matches"]:
                    errors.append(f"consumer contract {index} actual id mismatch")
                if not check["hash_matches"]:
                    errors.append(f"consumer contract {index} actual hash mismatch")
            else:
                errors.append(f"consumer contract {index} actual file missing")
            external_checks.append(check)
    if observed_ids != EXPECTED_CONSUMER_IDS:
        errors.append("consumer contract ids do not match the frozen v0.2 set")

    conformance = lock.get("conformance")
    if not isinstance(conformance, dict) or conformance.get("status") != "pass_unpublished_candidates":
        errors.append("candidate conformance receipt is missing")
    else:
        if conformance.get("producer_validated_consumer_fixture") is not True or conformance.get("consumer_validated_producer_fixture") is not True:
            errors.append("bidirectional fixture conformance is incomplete")
    boundaries = lock.get("boundaries")
    required_false = {
        "shared_cwd_required",
        "absolute_path_dependency_allowed",
        "upstream_fulfilled_equals_downstream_accepted",
        "soft_evidence_may_be_promoted_without_independent_support",
        "real_gui_validated",
        "business_acceptance_validated",
        "both_candidates_published",
    }
    if not isinstance(boundaries, dict) or any(boundaries.get(field) is not False for field in required_false):
        errors.append("bridge boundaries are invalid")

    errors = sorted(set(errors))
    return {
        "schema": "public.residential_bridge_validation.v0.2",
        "status": "pass" if not errors else "fail",
        "passed": not errors,
        "error_count": len(errors),
        "errors": errors,
        "producer_schema_id": producer.get("$id"),
        "consumer_contract_ids": sorted(observed_ids),
        "consumer_root_checked": consumer_root is not None,
        "external_checks": external_checks,
        "shared_cwd_required": False,
        "network_accessed": False,
        "platform_opened": False,
        "real_gui_validated": False,
        "business_acceptance_validated": False,
        "external_write_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--consumer-root", type=Path)
    args = parser.parse_args()
    receipt = validate(json.loads(args.lock.read_text(encoding="utf-8")), args.consumer_root)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
