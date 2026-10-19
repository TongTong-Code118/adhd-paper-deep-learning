"""Generate five PNG preview images with the independent rendering core."""
from pathlib import Path
import sys
import json
import base64

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from adhd_paper_mcp.server import render_tool

def main():
    data=json.loads((ROOT/"examples/tool-inputs.json").read_text(encoding="utf-8"))
    destination=ROOT/"examples"
    destination.mkdir(exist_ok=True)
    for tool,args in data.items():
        result=render_tool(tool,args)
        if result.get("isError"):
            raise RuntimeError(tool+": "+result["content"][0]["text"])
        image=next(block for block in result["content"] if block["type"]=="image")
        (destination/f"{tool}.png").write_bytes(base64.b64decode(image["data"]))
        print("Rendered",tool)

if __name__=="__main__":
    main()
