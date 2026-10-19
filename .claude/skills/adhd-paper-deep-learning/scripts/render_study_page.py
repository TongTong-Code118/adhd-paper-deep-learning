"""Build a self-contained, keyboard-friendly paper study page from verified JSON.

Usage: python render_study_page.py lesson.json lesson.html
No third-party packages, network access, or PDF parsing are required.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "study-page-template.html"


def clean(value: object, label: str, limit: int = 600) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f"{label} exceeds {limit} characters")
    return html.escape(value, quote=True)


def optional(value: object, label: str, limit: int = 600) -> str:
    return "" if value is None or value == "" else clean(value, label, limit)


def points(values: object, label: str, maximum: int = 4) -> str:
    if values is None:
        return ""
    if not isinstance(values, list) or len(values) > maximum:
        raise ValueError(f"{label} must be a list of at most {maximum} items")
    return "".join(f"<li>{clean(item, label + ' item')}</li>" for item in values)


def field(label: str, value: str) -> str:
    return f'<div class="fact"><dt>{label}</dt><dd>{value}</dd></div>'


def render(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    title = clean(data.get("title"), "title", 140)
    source = clean(data.get("source"), "source", 220)
    question = clean(data.get("question"), "question")
    claim = clean(data.get("claim"), "claim")
    caveat = optional(data.get("caveat"), "caveat")
    sections = data.get("sections")
    if not isinstance(sections, list) or not 1 <= len(sections) <= 12:
        raise ValueError("sections must contain 1–12 items")

    nav = []
    map_items = []
    panels = []
    for index, section in enumerate(sections, 1):
        if not isinstance(section, dict):
            raise ValueError(f"sections[{index}] must be an object")
        prefix = f"sections[{index}]"
        heading = clean(section.get("title"), prefix + ".title", 100)
        section_source = clean(section.get("source"), prefix + ".source", 160)
        section_question = clean(section.get("question"), prefix + ".question")
        role = clean(section.get("role"), prefix + ".role")
        bridge = clean(section.get("bridge"), prefix + ".bridge")
        takeaway = clean(section.get("takeaway"), prefix + ".takeaway")
        key_points = points(section.get("points"), prefix + ".points", 3)
        evidence = optional(section.get("evidence"), prefix + ".evidence")
        limit = optional(section.get("limit"), prefix + ".limit")
        concept = section.get("concept")
        recall = section.get("recall")
        concept_html = ""
        if concept is not None:
            if not isinstance(concept, dict):
                raise ValueError(prefix + ".concept must be an object")
            term = clean(concept.get("term"), prefix + ".concept.term", 100)
            steps = [
                ("先用类比理解", "analogy"),
                ("对应到论文", "mapping"),
                ("真实机制", "mechanism"),
                ("具体例子", "example"),
                ("类比边界", "boundary"),
            ]
            facts = "".join(field(label, clean(concept.get(key), prefix + ".concept." + key)) for label, key in steps)
            concept_html = f'<section class="module"><h3>关键概念 · {term}</h3><dl class="facts">{facts}</dl></section>'
        recall_html = ""
        if recall is not None:
            if not isinstance(recall, dict):
                raise ValueError(prefix + ".recall must be an object")
            prompt = clean(recall.get("question"), prefix + ".recall.question")
            answer = clean(recall.get("answer"), prefix + ".recall.answer")
            recall_html = f'<section class="module recall"><h3>试着回忆（可跳过）</h3><p>{prompt}</p><details><summary>想好后查看答案</summary><p>{answer}</p></details></section>'
        points_html = f'<section class="module"><h3>本节抓住这三点</h3><ul>{key_points}</ul></section>' if key_points else ""
        evidence_html = f'<section class="module evidence"><h3>证据与边界</h3><dl class="facts">{field("原文支持", evidence) if evidence else ""}{field("不能推出", limit) if limit else ""}</dl></section>' if evidence or limit else ""
        nav.append(f'<button class="nav-button" type="button" data-target="{index}" aria-controls="panel-{index}"><span>{index:02d}</span>{heading}</button>')
        map_items.append(f'<button class="map-card" type="button" data-target="{index}"><span class="map-number">{index:02d}</span><strong>{heading}</strong><small>{role}</small></button>')
        panels.append(f'''<article class="panel" id="panel-{index}" data-panel="{index}" hidden tabindex="-1">
          <div class="eyebrow">第 {index} / {len(sections)} 节 · {section_source}</div>
          <h2>{heading}</h2>
          <p class="lead">{section_question}</p>
          <section class="module"><h3>进入本节前，先回答三问</h3><dl class="facts">
          {field("回答什么", section_question)}{field("全篇作用", role)}{field("如何承接", bridge)}
          </dl></section>
          {points_html}{concept_html}{evidence_html}
          <section class="takeaway"><span>离开本节前记住</span><p>{takeaway}</p></section>
          {recall_html}
        </article>''')

    overview_caveat = f'<p class="caveat"><strong>阅读边界：</strong>{caveat}</p>' if caveat else ""
    overview = f'''<article class="panel" id="panel-0" data-panel="0" tabindex="-1">
      <div class="eyebrow">论文总览 · {source}</div>
      <h2>先找到整篇论文的方向</h2>
      <dl class="facts overview-facts">{field("研究问题", question)}{field("作者主张", claim)}</dl>
      {overview_caveat}
      <h3>阅读地图</h3><p class="muted">选一节进入；每次只看一个重点。</p>
      <div class="map" aria-label="论文阅读地图">{''.join(map_items)}</div>
      <p class="source-note">章节、证据和数字应依据原文核实；页面只呈现输入内容，不会自动审查论文。</p>
    </article>'''
    template = TEMPLATE.read_text(encoding="utf-8")
    return (template.replace("__TITLE__", title)
                    .replace("__NAV__", "".join(nav))
                    .replace("__PANELS__", overview + "".join(panels))
                    .replace("__COUNT__", str(len(sections))))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="verified lesson JSON")
    parser.add_argument("output", type=Path, help="self-contained HTML output")
    args = parser.parse_args()
    try:
        page = render(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(page, encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Cannot render study page: {exc}", file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
