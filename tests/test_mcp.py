"""Offline protocol + rendering tests; no network, account or MCP SDK needed."""
from __future__ import annotations
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"
sys.path.insert(0,str(SRC))
from adhd_paper_mcp.server import dispatch,catalog,render_tool

EXAMPLES=json.loads((ROOT/"examples/tool-inputs.json").read_text(encoding="utf-8"))
EXPECTED=set(EXAMPLES)

class McpTests(unittest.TestCase):
    def test_initialize_and_supported_protocol_version(self):
        response=dispatch({"jsonrpc":"2.0","id":1,"method":"initialize",
                            "params":{"protocolVersion":"2025-06-18","capabilities":{},
                                      "clientInfo":{"name":"offline-client","version":"0"}}})
        self.assertEqual(response["result"]["protocolVersion"],"2025-06-18")
        self.assertIn("tools",response["result"]["capabilities"])

    def test_list_has_five_read_only_tools(self):
        tools=dispatch({"jsonrpc":"2.0","id":2,"method":"tools/list"})["result"]["tools"]
        self.assertEqual({t["name"] for t in tools},EXPECTED)
        for t in tools:
            self.assertTrue(t["annotations"]["readOnlyHint"])
            self.assertFalse(t["annotations"]["openWorldHint"])

    def test_notifications_not_acknowledged(self):
        self.assertIsNone(dispatch({"jsonrpc":"2.0","method":"notifications/initialized"}))

    def test_actual_png_for_each_tool(self):
        for name,args in EXAMPLES.items():
            with self.subTest(tool=name):
                resp=render_tool(name,args)
                self.assertFalse(resp["isError"],resp["content"])
                block=next(c for c in resp["content"] if c["type"]=="image")
                self.assertEqual(block["mimeType"],"image/png")
                data=base64.b64decode(block["data"],validate=True)
                self.assertTrue(data.startswith(b"\x89PNG"))
                im=Image.open(io.BytesIO(data))
                self.assertGreaterEqual(im.width,1000)
                self.assertGreaterEqual(im.height,650)

    def test_five_node_vertical_flow_has_footer_after_last_card(self):
        args=dict(EXAMPLES["render_paper_map"])
        args["nodes"]=args["nodes"]+[{"title":"进一步研究","detail":"新样本与新问题","role":"证据边界"}]
        args["relationships"]=args["relationships"]+["延伸讨论"]
        resp=render_tool("render_paper_map",args)
        self.assertFalse(resp["isError"],resp["content"])
        block=next(x for x in resp["content"] if x["type"]=="image")
        with Image.open(io.BytesIO(base64.b64decode(block["data"]))) as im:
            self.assertGreater(im.height,1250)

    def test_invalid_input_has_error_without_image(self):
        args={"title":"no other fields"}
        resp=render_tool("render_paper_map",args)
        self.assertTrue(resp["isError"])
        self.assertFalse(any(x["type"]=="image" for x in resp["content"]))

    def test_wrong_relationship_count_rejected(self):
        args=dict(EXAMPLES["render_paper_map"])
        args["relationships"]=[]
        self.assertTrue(render_tool("render_paper_map",args)["isError"])

    def test_unknown_method_and_name(self):
        bad=dispatch({"jsonrpc":"2.0","id":13,"method":"unexpected/operation"})
        self.assertEqual(bad["error"]["code"],-32601)
        bad_tool=dispatch({"jsonrpc":"2.0","id":2,"method":"tools/call",
                           "params":{"name":"delete_files","arguments":{}}})
        self.assertEqual(bad_tool["error"]["code"],-32602)

    def test_mcp_wire_returns_real_image(self):
        env=os.environ.copy()
        env["PYTHONPATH"]=str(SRC)+os.pathsep+env.get("PYTHONPATH","")
        frames=[
            {"jsonrpc":"2.0","id":1,"method":"initialize",
             "params":{"protocolVersion":"2025-06-18","capabilities":{},
                       "clientInfo":{"name":"stdio-e2e","version":"1.0"}}},
            {"jsonrpc":"2.0","method":"notifications/initialized"},
            {"jsonrpc":"2.0","id":2,"method":"tools/list"},
            {"jsonrpc":"2.0","id":3,"method":"tools/call",
             "params":{"name":"render_section_flow","arguments":EXAMPLES["render_section_flow"]}},
        ]
        input_data=("\n".join(json.dumps(f,ensure_ascii=False) for f in frames)+"\n").encode("utf-8")
        run=subprocess.run([sys.executable,"-m","adhd_paper_mcp"],
                           input=input_data,cwd=ROOT,env=env,stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,timeout=25)
        self.assertEqual(run.returncode,0,run.stderr.decode("utf-8","replace")[-300:])
        raw=run.stdout.decode("utf-8").splitlines()
        self.assertEqual(len(raw),3,"notifications must not produce a reply")
        events=[json.loads(x) for x in raw]
        self.assertEqual([x["id"] for x in events],[1,2,3])
        img=next(x for x in events[2]["result"]["content"] if x["type"]=="image")
        with Image.open(io.BytesIO(base64.b64decode(img["data"]))) as picture:
            self.assertEqual(picture.format,"PNG")

class ConfigTests(unittest.TestCase):
    def test_cross_platform_mcp_json(self):
        for name,field in [(".mcp.json","mcpServers"),
                           (".cursor/mcp.json","mcpServers"),
                           ("configs/vscode-mcp.example.json","servers"),
                           ("configs/copilot-cloud-mcp.json","mcpServers")]:
            with self.subTest(name=name):
                obj=json.loads((ROOT/name).read_text(encoding="utf-8"))
                self.assertIn("adhd-paper-visuals",obj[field])

    def test_canonical_skill_discoverable_and_synced(self):
        canon=ROOT/"skill"
        self.assertTrue((canon/"SKILL.md").exists())
        for location in (".github/skills",".claude/skills",".cursor/skills"):
            with self.subTest(location=location):
                mirror=ROOT/location/"adhd-paper-deep-learning"
                self.assertEqual((mirror/"SKILL.md").read_bytes(),
                                 (canon/"SKILL.md").read_bytes())
                self.assertTrue((mirror/"references/05-visual-design.md").exists())

if __name__=="__main__":
    unittest.main()
