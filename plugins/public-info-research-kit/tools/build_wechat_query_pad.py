#!/usr/bin/env python3
"""Build one-query-per-page WeChat copy pads with focus/copy guards.

The generated pages never open WeChat or read the system clipboard.  They
contain exactly one selectable readonly input.  Command+A and copy are blocked
unless that input has focus; copy confirmation is shown only when the complete
input value is selected.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path


TRANSPORT_MODE = "approved_single_query_pad_copy_v2"
SAFE_QUERY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_page(query_id: str, exact_query_text: str) -> str:
    title = html.escape(query_id, quote=True)
    value = html.escape(exact_query_text, quote=True)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="query-id" content="{title}">
<meta name="transport-mode" content="{TRANSPORT_MODE}">
<title>{title}</title>
<style>
:root{{color-scheme:light}}
*{{box-sizing:border-box}}
html,body{{margin:0;min-height:100%;background:#f8fafc}}
body{{display:grid;place-items:center;padding:8vh 6vw;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}
#exact-query{{width:min(1040px,88vw);min-height:88px;padding:18px 22px;border:2px solid #94a3b8;border-radius:14px;background:#fff;color:#111827;font-size:clamp(24px,3vw,42px);line-height:1.35;caret-color:#2563eb;user-select:text;-webkit-user-select:text}}
#exact-query:focus{{outline:4px solid rgba(37,99,235,.34);border-color:#2563eb;box-shadow:0 0 0 8px rgba(59,130,246,.16),0 0 28px rgba(37,99,235,.52)}}
#exact-query[data-copy-confirmed="true"]{{outline-color:rgba(6,182,212,.48);border-color:#0891b2;box-shadow:0 0 0 8px rgba(34,211,238,.24),0 0 0 14px rgba(37,99,235,.16),0 0 34px rgba(8,145,178,.58)}}
body[data-blocked="true"]{{box-shadow:inset 0 0 0 7px rgba(220,38,38,.72)}}
</style>
</head>
<body><input id="exact-query" type="text" readonly spellcheck="false" autocomplete="off" aria-label="exact query text" value="{value}"></body>
<script>
const input=document.getElementById('exact-query');
const exactSelected=()=>document.activeElement===input&&input.selectionStart===0&&input.selectionEnd===input.value.length;
const clearSignals=()=>{{input.dataset.copyConfirmed='false';document.body.dataset.blocked='false'}};
input.addEventListener('pointerdown',clearSignals);
input.addEventListener('focus',clearSignals);
document.addEventListener('keydown',event=>{{
  if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='a'&&document.activeElement!==input){{
    event.preventDefault();
    document.body.dataset.blocked='true';
    input.dataset.copyConfirmed='false';
  }}
}});
document.addEventListener('copy',event=>{{
  if(!exactSelected()){{
    event.preventDefault();
    document.body.dataset.blocked='true';
    input.dataset.copyConfirmed='false';
    return;
  }}
  document.body.dataset.blocked='false';
  input.dataset.copyConfirmed='true';
}});
document.addEventListener('selectionchange',()=>{{if(!exactSelected())input.dataset.copyConfirmed='false'}});
</script>
</html>
"""


def build(request_path: Path, output_dir: Path) -> dict[str, object]:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if request.get("channel") != "wechat":
        raise ValueError("request channel must be wechat")
    query_plan = request.get("query_plan")
    if not isinstance(query_plan, list) or not query_plan:
        raise ValueError("query_plan must be a non-empty list")

    seen: set[str] = set()
    pages: list[dict[str, object]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(query_plan, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"query_plan[{index}] must be an object")
        query_id = item.get("query_id")
        exact_query_text = item.get("exact_query_text")
        if not isinstance(query_id, str) or not SAFE_QUERY_ID.fullmatch(query_id):
            raise ValueError(f"invalid query_id at query_plan[{index}]")
        if query_id in seen:
            raise ValueError(f"duplicate query_id: {query_id}")
        if not isinstance(exact_query_text, str) or not exact_query_text or exact_query_text.strip() != exact_query_text:
            raise ValueError(f"exact_query_text must be non-empty without edge whitespace: {query_id}")
        if "\n" in exact_query_text or "\r" in exact_query_text:
            raise ValueError(f"exact_query_text must be one line: {query_id}")
        seen.add(query_id)
        page = render_page(query_id, exact_query_text)
        filename = f"{index:03d}_{query_id}.html"
        (output_dir / filename).write_text(page, encoding="utf-8")
        pages.append(
            {
                "queue_order": index,
                "query_id": query_id,
                "file": filename,
                "exact_query_text_sha256": sha256_text(exact_query_text),
                "page_sha256": sha256_text(page),
            }
        )

    manifest = {
        "schema": "wechat_single_query_pad_manifest.v2",
        "transport_mode": TRANSPORT_MODE,
        "task_id": request.get("task_id"),
        "source_request": request_path.name,
        "source_request_sha256": sha256_file(request_path),
        "page_count": len(pages),
        "pages": pages,
        "copy_contract": {
            "one_page_one_readonly_input": True,
            "other_selectable_body_text": False,
            "focus_receipt": "blue_focus_glow",
            "selection_receipt": "input_local_full_selection_only",
            "copy_receipt": "double_blue_copy_glow",
            "command_a_without_input_focus": "blocked",
            "copy_without_exact_input_selection": "blocked",
            "final_receipt": "wechat_green_focus_then_exact_visible_text_after_paste",
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.request.resolve(), args.output_dir.resolve())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
