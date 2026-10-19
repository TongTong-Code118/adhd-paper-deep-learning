"""Render an audited, self-contained paper study page.

Usage: python render_study_page.py paper.json paper.html
Build the inventory from the original paper before writing explanations.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
from pathlib import Path
import sys

TEMPLATE = Path(__file__).resolve().parents[1] / "assets/study-page-template.html"
MAGIC = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"),
         (b"GIF87a", "image/gif"), (b"GIF89a", "image/gif"))


def value(item: object, label: str, limit: int = 20000) -> str:
    if not isinstance(item, str) or not item.strip() or len(item) > limit:
        raise ValueError(f"{label} must be non-empty text of at most {limit} characters")
    return item.strip()


def esc(item: object, label: str, limit: int = 20000) -> str:
    return html.escape(value(item, label, limit), quote=True)


def items(data: object, label: str, nonempty: bool = False) -> list:
    if not isinstance(data, list) or (nonempty and not data):
        raise ValueError(f"{label} must be {'a non-empty' if nonempty else 'a'} list")
    return data


def fact(label: str, content: str) -> str:
    return f'<div class="fact"><dt>{label}</dt><dd>{content}</dd></div>'


def validate_inventory(data: dict) -> tuple[list, list, list]:
    inv = data.get("inventory")
    if not isinstance(inv, dict):
        raise ValueError("inventory must be made independently from the original paper")
    sections = items(inv.get("sections"), "inventory.sections", True)
    units = items(inv.get("units"), "inventory.units", True)
    visuals = items(inv.get("visuals"), "inventory.visuals")
    def unique(seq: list, label: str) -> None:
        if len(seq) != len(set(seq)):
            raise ValueError(f"{label} has duplicate ids")
    for i, s in enumerate(sections):
        if not isinstance(s, dict):
            raise ValueError(f"inventory.sections[{i}] must be an object")
        for key in ("id", "title", "source"):
            value(s.get(key), f"inventory.sections[{i}].{key}")
        if not isinstance(s.get("number"), str):
            raise ValueError(f"inventory.sections[{i}].number must be text (empty for unnumbered)")
    sids = [s["id"] for s in sections]
    unique(sids, "inventory.sections")
    for i, u in enumerate(units):
        if not isinstance(u, dict):
            raise ValueError(f"inventory.units[{i}] must be an object")
        for key in ("id", "section_id", "source"):
            value(u.get(key), f"inventory.units[{i}].{key}")
        if u["section_id"] not in sids:
            raise ValueError(f"unit {u['id']} has unknown section")
    unique([u["id"] for u in units], "inventory.units")
    for i, v in enumerate(visuals):
        if not isinstance(v, dict) or v.get("kind") not in ("figure", "table"):
            raise ValueError(f"inventory.visuals[{i}] must be a figure/table object")
        for key in ("id", "number", "caption", "source", "section_id"):
            value(v.get(key), f"inventory.visuals[{i}].{key}")
        if v["section_id"] not in sids:
            raise ValueError(f"visual {v['id']} has unknown section")
    unique([v["id"] for v in visuals], "inventory.visuals")
    return sections, units, visuals


def image_uri(asset: object, root: Path, label: str) -> str:
    rel = Path(value(asset, label, 1000))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"{label} must be a relative path inside the input directory")
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{label} escapes the input directory")
    binary = path.read_bytes()
    mime = next((m for signature, m in MAGIC if binary.startswith(signature)), None)
    if binary.startswith(b"RIFF") and binary[8:12] == b"WEBP":
        mime = "image/webp"
    if mime is None:
        raise ValueError(f"{label} must be PNG, JPEG, WebP or GIF")
    return f"data:{mime};base64,{base64.b64encode(binary).decode('ascii')}"


def render(data: dict, asset_root: Path | None = None) -> str:
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    title = esc(data.get("title"), "title", 140)
    source = esc(data.get("source"), "source", 300)
    question = esc(data.get("question"), "question")
    claim = esc(data.get("claim"), "claim")
    original_sections, units, visuals = validate_inventory(data)
    sections = items(data.get("sections"), "sections", True)
    if len(sections) != len(original_sections):
        raise ValueError("sections must exactly match inventory.sections; no subsection may be skipped")
    unit_order = [u["id"] for u in units]
    visual_order = [v["id"] for v in visuals]
    visual_map = {v["id"]: v for v in visuals}
    seen_units, seen_visuals = [], []
    nav, cards, panels = [], [], []
    root = Path(asset_root or ".")
    for i, (s, original) in enumerate(zip(sections, original_sections), 1):
        if not isinstance(s, dict):
            raise ValueError(f"sections[{i}] must be an object")
        for key in ("id", "number", "title", "source"):
            if s.get(key) != original[key]:
                raise ValueError(f"sections[{i}].{key} must match original inventory and order")
        sid, number = original["id"], original["number"]
        heading = esc(original["title"], f"sections[{i}].title", 200)
        display = esc((number + " " if number else "") + original["title"], "heading", 250)
        loc = esc(original["source"], f"sections[{i}].source", 300)
        q = esc(s.get("question"), f"sections[{i}].question")
        role = esc(s.get("role"), f"sections[{i}].role")
        bridge = esc(s.get("bridge"), f"sections[{i}].bridge")
        takeaway = esc(s.get("takeaway"), f"sections[{i}].takeaway")
        depth = min(number.count(".") + 1, 5) if number else 1
        body = []
        for j, block in enumerate(items(s.get("blocks"), f"sections[{i}].blocks", True), 1):
            label = f"sections[{i}].blocks[{j}]"
            if not isinstance(block, dict):
                raise ValueError(f"{label} must be an object")
            covers = items(block.get("covers"), label + ".covers", True)
            own = {u["id"] for u in units if u["section_id"] == sid}
            for uid in covers:
                if uid not in own:
                    raise ValueError(f"{label} references unknown/wrong-section unit {uid}")
                seen_units.append(uid)
            note = esc(block.get("source"), label + ".source", 300)
            if block.get("type") == "explanation":
                prose = esc(block.get("text"), label + ".text")
                body.append(f'<section class="module text-block"><p>{prose}</p><small class="source-tag">{note}</small></section>')
            elif block.get("type") in ("figure", "table"):
                vid = value(block.get("id"), label + ".id", 100)
                v = visual_map.get(vid)
                if not v or v["section_id"] != sid or v["kind"] != block["type"]:
                    raise ValueError(f"{label} has unknown/wrong-section figure or table {vid}")
                seen_visuals.append(vid)
                uri = image_uri(block.get("asset"), root, label + ".asset")
                alt = esc(block.get("alt"), label + ".alt", 1000)
                caption = esc(v["caption"], label + ".caption", 3000)
                n = esc(v["number"], label + ".number", 100)
                look = esc(block.get("look"), label + ".look")
                meaning = esc(block.get("meaning"), label + ".meaning")
                limit = esc(block.get("limit"), label + ".limit")
                kind = "原图" if block["type"] == "figure" else "原表"
                body.append(f'<figure class="module original-visual"><div class="visual-label">{kind} {n} · 原文原貌</div><button class="zoom-open" type="button" aria-label="放大{kind} {n}"><img src="{uri}" alt="{alt}" loading="lazy" decoding="async"><span>点击放大原图</span></button><figcaption>{caption}</figcaption><dl class="facts">{fact("看哪里", look)}{fact("说明什么", meaning)}{fact("不能说明什么", limit)}</dl><small class="source-tag">{note}</small></figure>')
            else:
                raise ValueError(f"{label}.type must be explanation, figure or table")
        nav.append(f'<button class="nav-button depth-{depth}" type="button" data-target="{i}" aria-controls="panel-{i}"><span>{esc(number or "·", "number", 60)}</span>{heading}</button>')
        cards.append(f'<button class="map-card" type="button" data-target="{i}"><span class="map-number">{esc(number or "·", "number", 60)}</span><strong>{heading}</strong><small>{role}</small></button>')
        panels.append(f'<article class="panel" id="panel-{i}" data-panel="{i}" hidden tabindex="-1"><div class="eyebrow">原文顺序 {i} / {len(sections)} · {loc}</div><h2>{display}</h2><p class="lead">{q}</p><section class="module"><h3>进入本节前，先回答三问</h3><dl class="facts">{fact("回答什么", q)}{fact("全篇作用", role)}{fact("如何承接", bridge)}</dl></section>{"".join(body)}<section class="takeaway"><span>离开本节前记住</span><p>{takeaway}</p></section></article>')
    if seen_visuals != visual_order:
        raise ValueError(f"original figure/table coverage/order mismatch; missing={[x for x in visual_order if x not in seen_visuals]}")
    if seen_units != unit_order:
        raise ValueError(f"source-unit coverage/order mismatch; missing={[x for x in unit_order if x not in seen_units]}")
    overview = f'<article class="panel" id="panel-0" data-panel="0" tabindex="-1"><div class="eyebrow">论文总览 · {source}</div><h2>先找到整篇论文的方向</h2><dl class="facts overview-facts">{fact("研究问题", question)}{fact("作者主张", claim)}</dl><p class="coverage">原文章节 {len(sections)} / {len(original_sections)} · 内容单元 {len(seen_units)} / {len(units)} · 原图原表 {len(seen_visuals)} / {len(visuals)}</p><h3>原文阅读路径</h3><p class="muted">依照论文的真实顺序；选择一节进入。</p><div class="map" aria-label="论文原文目录">{"".join(cards)}</div><p class="source-note">覆盖计数依赖事先从原文建立的清单。若清单不完整，计数不能证明整篇论文完整。</p></article>'
    template = TEMPLATE.read_text(encoding="utf-8")
    return template.replace("__TITLE__", title).replace("__NAV__", "".join(nav)).replace("__PANELS__", overview + "".join(panels)).replace("__COUNT__", str(len(sections)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        page = render(json.loads(args.input.read_text(encoding="utf-8")), args.input.parent)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(page, encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Cannot render study page: {exc}", file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
