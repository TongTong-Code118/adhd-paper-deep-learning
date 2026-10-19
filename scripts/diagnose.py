"""End-to-end MCP diagnostic: real stdio handshake and ImageContent checks."""
from pathlib import Path
import os
import sys
import json
import base64
import io
import subprocess
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SAMPLES=json.loads((ROOT/"examples/tool-inputs.json").read_text(encoding="utf-8"))
def diagnose():
    env=os.environ.copy()
    # Works before pip installation as well, while README still recommends pip.
    env["PYTHONPATH"]=str(ROOT/"src")+os.pathsep+env.get("PYTHONPATH","")
    msgs=[
        {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
           "protocolVersion":"2025-06-18","capabilities":{},
           "clientInfo":{"name":"adhd-diagnostic","version":"1"}}},
        {"jsonrpc":"2.0","method":"notifications/initialized"},
        {"jsonrpc":"2.0","id":2,"method":"tools/list"},
    ]
    msgs.extend([
        {"jsonrpc":"2.0","id":10+i,"method":"tools/call",
         "params":{"name":name,"arguments":args}}
        for i,(name,args) in enumerate(SAMPLES.items())
    ])
    payload=("\n".join(json.dumps(m,ensure_ascii=False) for m in msgs)+"\n").encode("utf-8")
    r=subprocess.run([sys.executable,"-m","adhd_paper_mcp"],input=payload,
        cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
    if r.returncode:
        raise RuntimeError("Server exited with error:\n"+r.stderr.decode("utf-8","replace")[-600:])
    responses=[json.loads(line) for line in r.stdout.splitlines()]
    expected_count=2+len(SAMPLES)
    if len(responses)!=expected_count:
        raise RuntimeError(f"Expected {expected_count} responses, got {len(responses)}")
    announced={tool["name"] for tool in responses[1]["result"]["tools"]}
    if announced!=set(SAMPLES):
        raise RuntimeError("Unexpected tool catalog")
    print("PASS: MCP initialize and tools/list (5 tools)")
    for resp in responses[2:]:
        blocks=resp["result"]["content"]
        if resp["result"].get("isError"):
            raise RuntimeError(blocks[0]["text"])
        image=next((x for x in blocks if x.get("type")=="image"),None)
        if not image or image.get("mimeType")!="image/png":
            raise RuntimeError("Tool did not return image/png")
        with Image.open(io.BytesIO(base64.b64decode(image["data"]))) as preview:
            preview.verify()
        print(f"PASS: real MCP tool call #{resp['id']} → PNG image")
    print("PASS: every registered tool returned an actual image; host UI display must be tested separately.")
if __name__=="__main__":
    try: diagnose()
    except Exception as exc:
        print("FAIL:",exc,file=sys.stderr)
        sys.exit(1)
