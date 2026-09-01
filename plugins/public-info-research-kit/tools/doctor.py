#!/usr/bin/env python3
"""Optional read-only self-diagnostic; offline by default and never installs dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PLUGIN_ID = "public-info-research-kit@public-info-research-public"
COMPUTER_USE_PLUGIN_IDS = {"computer-use@openai-bundled"}
SUPPORTED = {(3, 12), (3, 13), (3, 14)}


def current_release_version() -> str:
    path = ROOT / ".codex-plugin/plugin.json"
    try:
        return str(json.loads(path.read_text(encoding="utf-8"))["version"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return "unknown"


RELEASE_VERSION = current_release_version()


def command(args: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return result.returncode, result.stdout


def finding(name: str, status: str, action: str, observed: object = None) -> dict[str, Any]:
    return {"name": name, "status": status, "observed": observed, "action": action}


def discover_supported_pythons() -> list[dict[str, str]]:
    rows = []
    seen = set()
    for name in ("python3.14", "python3.13", "python3.12"):
        path = shutil.which(name)
        if not path or path in seen:
            continue
        seen.add(path)
        code, output = command([path, "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"])
        if code != 0:
            continue
        version = output.strip()
        parts = version.split(".")
        if len(parts) >= 2 and tuple(map(int, parts[:2])) in SUPPORTED:
            rows.append({"command": name, "version": version})
    return rows


def locate_codex() -> str | None:
    codex = shutil.which("codex")
    if codex:
        return codex
    for candidate in (
        "/Applications/Codex.app/Contents/Resources/codex",
        "/Applications/ChatGPT.app/Contents/Resources/codex",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def read_plugin_inventory(codex: str | None) -> tuple[list[dict[str, Any]], str | None]:
    if not codex:
        return [], "codex_cli_missing"
    code, output = command([codex, "plugin", "list", "--json"])
    if code != 0:
        return [], "plugin_list_failed"
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return [], "plugin_list_invalid_json"
    rows = payload.get("installed") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return [], "plugin_list_missing_installed"
    return [row for row in rows if isinstance(row, dict)], None


def find_plugin(rows: list[dict[str, Any]], *, plugin_ids: set[str] | None = None, name: str | None = None) -> dict[str, Any] | None:
    for row in rows:
        if plugin_ids and row.get("pluginId") in plugin_ids:
            return row
        if name and row.get("name") == name:
            return row
    return None


def computer_use_finding(rows: list[dict[str, Any]], inventory_error: str | None = None) -> dict[str, Any]:
    row = find_plugin(rows, plugin_ids=COMPUTER_USE_PLUGIN_IDS, name="computer-use")
    observed = {
        "installed": bool(row and row.get("installed") is True),
        "enabled": bool(row and row.get("enabled") is True),
        "plugin_id": row.get("pluginId") if row else None,
        "version": row.get("version") if row else None,
        "inventory_error": inventory_error,
    }
    if not row or row.get("installed") is not True:
        return finding(
            "computer_use_plugin",
            "gap",
            "如需微信或小红书 GUI 能力，请终端用户在 Codex Plugins 中自行安装 Computer Use；本工具不会代装",
            observed,
        )
    if row.get("enabled") is not True:
        return finding(
            "computer_use_plugin",
            "gap",
            "如需微信或小红书 GUI 能力，请终端用户在 Codex Plugins 中自行启用 Computer Use；本工具不会代启用",
            observed,
        )
    return finding(
        "computer_use_plugin",
        "pass",
        "已检测到安装并启用；系统权限和真实可用性仍由终端用户确认并通过逐机 smoke 验收",
        observed,
    )


def manual_prerequisite_findings(channels: set[str]) -> list[dict[str, Any]]:
    rows = [
        finding(
            "computer_use_macos_permissions",
            "notice",
            "如需 GUI 渠道，请终端用户自行授予 Computer Use 所需的屏幕录制与辅助功能权限；doctor 不读取系统权限数据库、不修改权限",
            "not_verified_by_doctor",
        )
    ]
    if "wechat" in channels:
        rows.append(
            finding(
                "wechat_end_user_session",
                "notice",
                "终端用户需登录自己的微信，并在首次真实 smoke 前手动打开公开搜一搜主页面",
                "not_inspected_by_doctor",
            )
        )
    if "xhs" in channels:
        rows.append(
            finding(
                "xhs_end_user_session",
                "notice",
                "终端用户需在自己的正常可见 Chrome 中登录小红书；doctor 不打开浏览器、不读取 profile 或登录态",
                "not_inspected_by_doctor",
            )
        )
    return rows


def release_manifest_integrity() -> tuple[bool, dict[str, Any]]:
    manifest_path = REPO / "PUBLIC_BETA_MANIFEST.json"
    if not manifest_path.is_file():
        return False, {"reason": "manifest_missing"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, {"reason": type(exc).__name__}
    failures = []
    for entry in manifest.get("files") or []:
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            failures.append({"path": relative, "reason": "invalid_path"})
            continue
        path = REPO / relative
        if not path.is_file():
            failures.append({"path": relative, "reason": "missing"})
            continue
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != entry.get("sha256") or len(payload) != entry.get("bytes"):
            failures.append({"path": relative, "reason": "hash_or_size_mismatch"})
    valid = manifest.get("version") == RELEASE_VERSION and manifest.get("skill_count") == 7 and not failures
    return valid, {
        "version": manifest.get("version"),
        "file_count": len(manifest.get("files") or []),
        "failures": failures,
    }


def network_finding(enabled: bool) -> dict[str, Any]:
    if not enabled:
        return finding("tls", "not_checked", "默认离线；只有排查网络依赖时才显式加 --network-probe", None)
    try:
        urllib.request.urlopen("https://pypi.org/simple/pypdf/", timeout=6, context=ssl.create_default_context()).close()
        return finding("tls", "pass", "无需处理", "pypi.org")
    except Exception as exc:
        return finding("tls", "gap", "检查系统时间、企业证书链或代理 TLS；不要关闭证书校验", type(exc).__name__)


def build_report(*, channels: set[str], network_probe: bool) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    version = sys.version_info[:3]
    current = ".".join(map(str, version))
    supported_pythons = discover_supported_pythons()
    if version[:2] in SUPPORTED:
        rows.append(finding("python", "pass", "当前解释器可直接使用", {"current": current, "command": Path(sys.executable).name}))
    elif supported_pythons:
        selected = supported_pythons[0]
        rows.append(finding("python", "pass", f"系统默认 Python 为 {current}；需要 Python 工具时使用 {selected['command']}", {"current": current, "available": supported_pythons}))
    else:
        rows.append(finding("python", "gap", "安装 Python 3.12、3.13 或 3.14 后重新运行；Plugin 注册本身不依赖 Python", {"current": current, "available": []}))
    for name in ("node", "npm"):
        path = shutil.which(name)
        rows.append(finding(name, "pass" if path else "optional", "仅开发或本地浏览器 fixture 需要；普通使用不必安装", bool(path)))
    proxy_names = ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY")
    present = [name for name in proxy_names if os.environ.get(name) or os.environ.get(name.lower())]
    rows.append(finding("proxy", "notice" if present else "pass", "确认代理与组织策略一致；doctor 不显示代理值", present))
    rows.append(network_finding(network_probe))

    codex = locate_codex()
    rows.append(finding("codex_cli", "pass" if codex else "gap", "确认 Codex 命令行工具可用", bool(codex)))
    inventory, inventory_error = read_plugin_inventory(codex)
    public_plugin = find_plugin(inventory, plugin_ids={PLUGIN_ID}, name="public-info-research-kit")
    plugin_visible = bool(
        public_plugin
        and public_plugin.get("installed") is True
        and public_plugin.get("enabled") is True
        and public_plugin.get("version") == RELEASE_VERSION
    )
    rows.append(
        finding(
            "plugin_visibility",
            "pass" if plugin_visible else "gap",
            "在 Plugin 页面安装或更新到当前版本；当前任务未刷新时新建任务；仍不可见时再重启 Codex 排错",
            {
                "visible_current_version": plugin_visible,
                "expected_version": RELEASE_VERSION,
                "installed_version": public_plugin.get("version") if public_plugin else None,
                "inventory_error": inventory_error,
            },
        )
    )

    needs_gui = bool(channels & {"wechat", "xhs"})
    computer_use = computer_use_finding(inventory, inventory_error)
    if needs_gui:
        rows.append(computer_use)
        rows.extend(manual_prerequisite_findings(channels))

    skills = sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md"))
    rows.append(finding("skill_count", "pass" if len(skills) == 7 else "gap", "安装包必须恰好包含七个 Skill", skills))
    manifest_ok, manifest_observed = release_manifest_integrity()
    rows.append(finding("release_manifest_integrity", "pass" if manifest_ok else "gap", "重新从公开仓安装或更新；不要继续使用文件缺失或哈希不一致的副本", manifest_observed))
    sensitive = []
    for path in REPO.rglob("*"):
        if path.is_file() and path.name.lower() in {".env", "cookies.sqlite", "storage_state.json", "credentials.json"}:
            sensitive.append(str(path.relative_to(REPO)))
    rows.append(finding("sensitive_files", "pass" if not sensitive else "gap", "删除凭证或账号态文件并轮换相关凭证", sensitive))

    gaps = [row for row in rows if row["status"] == "gap"]
    gui_state = "not_requested"
    if needs_gui:
        gui_state = "prerequisites_detected_user_confirmation_and_real_smoke_pending" if computer_use["status"] == "pass" else "computer_use_not_ready"
    return {
        "schema": "public_info_self_service_doctor.v2",
        "version": RELEASE_VERSION,
        "status": "pass" if not gaps else "gaps_detected",
        "requested_channels": sorted(channels),
        "checks": rows,
        "gap_count": len(gaps),
        "capability_readiness": {
            "non_gui": "candidate_ready" if manifest_ok and len(skills) == 7 else "package_gap",
            "wechat_xhs_gui": gui_state,
            "real_channel_smoke": "not_executed_by_doctor",
            "business_acceptance": "not_assessed_by_doctor",
        },
        "computer_use_policy": {
            "installation_owner": "end_user",
            "package_action": "remind_and_detect_only",
            "automatic_install": False,
            "automatic_enable": False,
            "automatic_permission_change": False,
            "login_operation": False,
        },
        "network_probe": "tls_only" if network_probe else "none",
        "credentials_read": False,
        "writes_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", choices=("all", "non_gui", "wechat", "xhs"), default="all")
    parser.add_argument("--network-probe", action="store_true", help="opt in to one TLS probe; default is fully offline")
    args = parser.parse_args()
    channels = {
        "all": {"non_gui", "wechat", "xhs"},
        "non_gui": {"non_gui"},
        "wechat": {"wechat"},
        "xhs": {"xhs"},
    }[args.channel]
    report = build_report(channels=channels, network_probe=args.network_probe)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
