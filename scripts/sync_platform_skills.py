"""Mirror the canonical Skill into each platform's project discovery directory.

    python scripts/sync_platform_skills.py
    python scripts/sync_platform_skills.py --check

Do not edit mirrored files manually; edit skill/ instead.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import shutil
import sys

ROOT=Path(__file__).resolve().parent.parent
NAME="adhd-paper-deep-learning"
SOURCE=ROOT/"skill"
TARGETS=[
    ROOT/".github/skills"/NAME,
    ROOT/".claude/skills"/NAME,
    ROOT/".cursor/skills"/NAME,
]
def source_files():
    return sorted(p.relative_to(SOURCE) for p in SOURCE.rglob("*") if p.is_file())
def sync(check=False):
    expected=source_files()
    if not expected or Path("SKILL.md") not in expected:
        raise RuntimeError("Canonical skill/SKILL.md missing")
    bad=[]
    for target in TARGETS:
        if check:
            existing=set(p.relative_to(target) for p in target.rglob("*") if p.is_file()) if target.exists() else set()
            mismatch=[p for p in expected if not (target/p).is_file() or (target/p).read_bytes()!=(SOURCE/p).read_bytes()]
            extra=existing-set(expected)
            if mismatch or extra:
                bad.append(str(target.relative_to(ROOT)) + f": stale {len(mismatch)}, extra {len(extra)}")
        else:
            if target.exists():shutil.rmtree(target)
            for rel in expected:
                dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(SOURCE/rel,dst)
            print("Synced:",target.relative_to(ROOT),"files:",len(expected))
    if check:
        if bad:
            print("FAIL Skill mirrors:\n"+ "\n".join(bad))
            return False
        print("PASS: all 3 project Skill mirrors exactly match canonical skill/")
    return True

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    sys.exit(0 if sync(args.check) else 1)
