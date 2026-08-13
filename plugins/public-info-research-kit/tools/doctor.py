#!/usr/bin/env python3
"""Optional read-only self-diagnostic for the 0.5.0 personal self-use beta."""

from __future__ import annotations

import json
import os
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PLUGIN_ID = "public-info-research-kit@public-info-research-public"
SUPPORTED = {(3, 12), (3, 13), (3, 14)}


def command(args: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return result.returncode, result.stdout


def finding(name: str, status: str, action: str, observed: object = None) -> dict:
    return {"name": name, "status": status, "observed": observed, "action": action}


def discover_supported_pythons() -> list[dict]:
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


def main() -> int:
    rows: list[dict] = []
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
    try:
        urllib.request.urlopen("https://pypi.org/simple/pypdf/", timeout=6, context=ssl.create_default_context()).close()
        rows.append(finding("tls", "pass", "无需处理", "pypi.org"))
    except Exception as exc:
        rows.append(finding("tls", "gap", "检查系统时间、企业证书链或代理 TLS；不要关闭证书校验", type(exc).__name__))
    codex = shutil.which("codex")
    if not codex:
        for candidate in ("/Applications/Codex.app/Contents/Resources/codex", "/Applications/ChatGPT.app/Contents/Resources/codex"):
            if Path(candidate).is_file():
                codex = candidate
                break
    rows.append(finding("codex_cli", "pass" if codex else "gap", "确认 Codex 命令行工具可用", bool(codex)))
    plugin_visible = False
    if codex:
        code, output = command([codex, "plugin", "list", "--json"])
        plugin_visible = code == 0 and PLUGIN_ID in output
    rows.append(finding("plugin_visibility", "pass" if plugin_visible else "gap", "在 Plugin 页面重新安装；当前任务未刷新时新建任务；仍不可见时再重启 Codex 排错", plugin_visible))
    skills = sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md"))
    rows.append(finding("skill_count", "pass" if len(skills) == 7 else "gap", "安装包必须恰好包含七个 Skill", skills))
    sensitive = []
    for path in REPO.rglob("*"):
        if path.is_file() and path.name.lower() in {".env", "cookies.sqlite", "storage_state.json", "credentials.json"}:
            sensitive.append(str(path.relative_to(REPO)))
    rows.append(finding("sensitive_files", "pass" if not sensitive else "gap", "删除凭证或账号态文件并轮换相关凭证", sensitive))
    gaps = [row for row in rows if row["status"] == "gap"]
    report = {"schema": "public_info_personal_self_use_doctor.v1", "version": "0.5.0", "status": "pass" if not gaps else "gaps_detected", "checks": rows, "gap_count": len(gaps), "network_probe": "tls_only", "credentials_read": False, "writes_performed": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not gaps else 2


if __name__ == "__main__":
    raise SystemExit(main())
