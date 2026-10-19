"""Offline static checks for a GitHub-uploadable multi-platform Skill/MCP repo."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tomllib
import xml.etree.ElementTree as ET
import re

ROOT=Path(__file__).resolve().parents[1]
NAME="adhd-paper-deep-learning"
REQUIRED=[
    "README.md","pyproject.toml",".mcp.json",".cursor/mcp.json",
    "configs/copilot-cloud-mcp.json","configs/vscode-mcp.example.json",
    ".github/workflows/test.yml",".github/workflows/copilot-setup-steps.yml",
    "skill/SKILL.md","skill/references/05-visual-design.md",
    "src/adhd_paper_mcp/server.py","src/adhd_paper_mcp/graphics.py",
    "scripts/sync_platform_skills.py","tests/test_mcp.py",
    "examples/tool-inputs.json","docs/index.html",
]
def validate():
    errors=[]
    for name in REQUIRED:
        if not (ROOT/name).is_file():
            errors.append("missing: "+name)
    for name in (".mcp.json",".cursor/mcp.json","configs/copilot-cloud-mcp.json","configs/vscode-mcp.example.json"):
        path=ROOT/name
        if not path.is_file():continue
        try:
            cfg=json.loads(path.read_text(encoding="utf-8"))
            keys=cfg.get("servers",cfg.get("mcpServers",{}))
            entry=keys["adhd-paper-visuals"]
            if entry.get("command")!="python":errors.append(name+": command should be python")
            if entry.get("args")!=["-m","adhd_paper_mcp"]:
                errors.append(name+": unexpected entrypoint")
            if name=="configs/copilot-cloud-mcp.json":
                if len(entry.get("tools",[]))!=5 or entry.get("type")!="local":
                    errors.append(name+": expected explicit tool allowlist")
        except Exception as exc:
            errors.append(name+": JSON invalid "+str(exc))
    try:
        pkg=tomllib.loads((ROOT/"pyproject.toml").read_text(encoding="utf-8"))
        if pkg["project"]["version"]!="5.0.0":errors.append("incorrect version")
    except Exception as exc:
        errors.append("pyproject invalid: "+str(exc))
    for skill in [ROOT/"skill",ROOT/".github/skills"/NAME,
                  ROOT/".claude/skills"/NAME,ROOT/".cursor/skills"/NAME]:
        filename=skill/"SKILL.md"
        if not filename.is_file():
            errors.append(str(filename)+" missing")
            continue
        content=filename.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            errors.append(str(filename)+": no YAML header")
        if "name: "+NAME not in content[:300]:
            errors.append(str(filename)+": wrong frontmatter skill name")
        for match in re.findall(r"\]\(([^)]+)\)",content):
            if "://" in match or match.startswith("#"):continue
            if not (skill/match).is_file():errors.append(str(filename)+": broken ref "+match)
    samples=ROOT/"examples/tool-inputs.json"
    if samples.is_file():
        try:
            data=json.loads(samples.read_text(encoding="utf-8"))
            if len(data)!=5:errors.append("should have five rendering samples")
            for name in data:
                img=ROOT/"examples"/(name+".png")
                if not img.is_file() or not img.read_bytes().startswith(b"\x89PNG"):
                    errors.append("missing PNG preview: "+name)
        except Exception as exc:
            errors.append("example inputs invalid: "+str(exc))
    for svg in (ROOT/"skill/assets/diagrams").glob("*.svg"):
        try:ET.parse(svg)
        except Exception as exc:errors.append("invalid SVG: "+str(svg)+str(exc))
    try:
        for container in ("github","claude","cursor"):
            parent={"github":".github","claude":".claude","cursor":".cursor"}[container]
            other=ROOT/parent/"skills"/NAME
            canon=ROOT/"skill"
            expected={p.relative_to(canon):p.read_bytes() for p in canon.rglob("*") if p.is_file()}
            actual={p.relative_to(other):p.read_bytes() for p in other.rglob("*") if p.is_file()}
            if expected!=actual:errors.append(container+" skill mirror out of sync")
    except Exception as exc:errors.append("mirror check error: "+str(exc))
    if errors:
        print("FAIL",len(errors),"problems")
        for e in errors:print("  -",e)
        return False
    print("PASS: 5 cross-platform MCP configurations + 3 matching Skill mirrors")
    print("PASS: Python package metadata, source references, 5 actual PNG examples")
    print("PASS: workflows, diagram resources and repository structure")
    return True

if __name__=="__main__":
    sys.exit(0 if validate() else 1)
