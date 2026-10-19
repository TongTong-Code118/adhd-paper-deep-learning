"""Stand-alone MCP stdio tool server.

Implements the MCP 2025-06-18 JSON-RPC stdio *tool* subset:
initialize, notifications/initialized, ping, tools/list, tools/call.
No HTTP, network, file writes or shell execution. Intentional read-only tools.

The transport is newline-delimited UTF-8 JSON-RPC; stdout is protocol-only.
Reference: https://modelcontextprotocol.io/specification/2025-06-18
"""
from __future__ import annotations
import base64
import json
import logging
import os
import time
import sys
from typing import Any

from . import __version__
from .graphics import build_png

logger=logging.getLogger("adhd-paper-mcp")
PROTOCOL="2025-06-18"
SUPPORTED={PROTOCOL,"2025-03-26","2024-11-05"}
MAX_INPUT_BYTES=120_000
MAX_TEXT_LENGTH=240

def str_field(title:str, maxlen:int=100):
    return {"type":"string","minLength":1,"maxLength":maxlen,"description":title}

def obj_props(fields,required=None):
    return {"type":"object","properties":fields,"required":list(required or fields),
            "additionalProperties":False}

def arr(item,min_n=1,max_n=7):
    return {"type":"array","items":item,"minItems":min_n,"maxItems":max_n}

def catalog():
    entry=obj_props({
        "title":str_field("节点真实标题（不能编造）",45),
        "detail":str_field("这一步的核心问题/说明",85),
        "role":str_field("本节点在整篇文章的角色",35)})
    stage=obj_props({
        "title":str_field("原文小节/操作名称",45),
        "question":str_field("这一环节回答什么问题",85),
        "purpose":str_field("本步骤为何需要",35)})
    mapping=obj_props({
        "everyday":str_field("日常类比中的元素",30),
        "academic":str_field("真实概念/变量",30),
        "relationship":str_field("两者为何对应",60)})
    symbol=obj_props({"symbol":str_field("符号",18),"meaning":str_field("含义",75)},
                     ["symbol","meaning"])
    symbol["properties"]["unit"]=str_field("单位（如有）",30)
    base={"title":str_field("简洁图标题",65),
          "subtitle":str_field("一行图的任务",95),
          "nodes":arr(entry,2,7),
          "relationships":arr(str_field("相邻节点之间的真实关系",20),1,6),
          "current_index":{"type":"integer","minimum":0,"maximum":6,"default":0},
          "source_note":str_field("原文定位与不能确定的内容。必须提供。",180)}
    schemas={
      "render_paper_map":obj_props(base,
          ["title","subtitle","nodes","relationships","source_note"]),
      "render_section_flow":obj_props({
          "section_title":str_field("原文真实章节标题",65),
          "stages":arr(stage,2,7),
          "relationships":arr(str_field("步骤之间的关系",20),1,6),
          "current_index":{"type":"integer","minimum":0,"maximum":6,"default":0},
          "source_note":str_field("原文节号/页码及不确定性说明",180)},
          ["section_title","stages","relationships","source_note"]),
      "render_concept_diagram":obj_props({
          "concept":str_field("真实概念名称",65),
          "everyday_analogy":str_field("日常场景/故事",125),
          "mappings":arr(mapping,1,3),
          "mechanism_steps":arr(str_field("真实机制步骤",58),2,4),
          "numeric_example":str_field("完整数值/定性情境示例及来源标签",135),
          "analogy_limit":str_field("生活类比失效的关键情况",105),
          "source_note":str_field("原文节号、证据与教学例子区分",180)}),
      "render_formula_structure":obj_props({
          "title":str_field("公式名称与原文编号",65),
          "formula":str_field("原式可读文本，不支持 LaTeX 排版，符号应有定义",110),
          "symbols":arr(symbol,1,4),
          "steps":arr(str_field("逐步推导或运算",55),2,4),
          "numeric_example":str_field("完整数字验算及来源",145),
          "limitation":str_field("成立条件或反例",115),
          "source_note":str_field("原文来源定位、是否教学示例",180)}),
      "render_evidence_prism":obj_props({
          "title":str_field("真实图号/表号与主题",65),
          "look_at":str_field("具体轴/单位/行列与关键比较",135),
          "supports":str_field("图表真正直接支持的结论",150),
          "cannot_conclude":str_field("不能推出的结论、混淆、局限",150),
          "source_note":str_field("原文位置、原图是否可见、数据是否模拟",180)}),
    }
    descriptions={
        "render_paper_map":"把已核实的论文章节职责转换为可见 PNG 论证流程图；不得臆造标题或因果箭头。输入来源注释必填。",
        "render_section_flow":"画当前章节的 2–7 步结构流程图，含每步任务与承接关系，返回真正的 PNG 图片。",
        "render_concept_diagram":"绘制一个晦涩概念的生活类比↔科学机制映射图，包含完整具体例子和类比失效边界。",
        "render_formula_structure":"将关键公式画成符号卡+逐步运算图；必须保留已知条件、数字验算及不成立的情形。",
        "render_evidence_prism":"绘制图表证据三棱镜：看哪里、说明什么、不能说明什么，阻止过度推断。",
    }
    return [{"name":key,"title":key.replace("_"," ").title(),
             "description":descriptions[key],"inputSchema":schema,
             "annotations":{"readOnlyHint":True,"destructiveHint":False,
                            "idempotentHint":True,"openWorldHint":False}}
            for key,schema in schemas.items()]

TOOLS={tool["name"]:tool for tool in catalog()}

def _validate(schema:dict, value:Any, path="arguments"):
    kind=schema.get("type")
    if kind=="object":
        if not isinstance(value,dict): raise ValueError(f"{path}: expected JSON object")
        for key in schema.get("required",[]):
            if key not in value:raise ValueError(f"{path}: missing '{key}'")
        if schema.get("additionalProperties") is False:
            extras=set(value)-set(schema.get("properties",{}))
            if extras:raise ValueError(f"{path}: unexpected field(s) {sorted(extras)}")
        for key,val in value.items():
            _validate(schema["properties"][key],val,f"{path}.{key}")
    elif kind=="string":
        if not isinstance(value,str):raise ValueError(f"{path}: expected text")
        if len(value.strip())<schema.get("minLength",0) or len(value)>schema.get("maxLength",MAX_TEXT_LENGTH):
            raise ValueError(f"{path}: invalid text length")
        if any(ord(ch)<32 and ch not in "\\n\\t" for ch in value):
            raise ValueError(f"{path}: control characters not allowed")
    elif kind=="integer":
        if type(value) is not int or not schema.get("minimum",-1_000_000)<=value<=schema.get("maximum",1_000_000):
            raise ValueError(f"{path}: integer out of range")
    elif kind=="array":
        if not isinstance(value,list):raise ValueError(f"{path}: expected array")
        if not schema.get("minItems",0)<=len(value)<=schema.get("maxItems",100):
            raise ValueError(f"{path}: invalid number of items")
        for i,child in enumerate(value):
            _validate(schema["items"],child,f"{path}[{i}]")

def validate_tool(name:str,args:Any):
    if name not in TOOLS: raise ValueError("unknown tool: "+name)
    _validate(TOOLS[name]["inputSchema"],args)
    if name in ("render_paper_map","render_section_flow"):
        nodes=args.get("nodes",args.get("stages",[]))
        if len(args["relationships"])!=len(nodes)-1:
            raise ValueError("相邻节点关系数量必须为节点数减一")
        if args.get("current_index",0)>=len(nodes):
            raise ValueError("current_index 超出了节点数量")
    return args

def render_tool(name:str,args:dict)->dict:
    try:
        validate_tool(name,args)
        image=build_png(name,args)
    except (ValueError,RuntimeError) as exc:
        return {"content":[{"type":"text","text":"无法绘图："+str(exc)}],"isError":True}
    # Actual rendered image delivered as MCP ImageContent.
    return {
      "content":[
          {"type":"text","text":f"已生成可见 PNG 图像：{args.get('title',args.get('section_title',args.get('concept','图示')))}。注意：图示内容依据调用者提供的材料，服务本身不核查论文事实。来源/局限：{args['source_note']}"},
          {"type":"image","data":base64.b64encode(image).decode("ascii"),"mimeType":"image/png"}
      ],
      "isError":False,
    }

def rpc_error(msg_id,code,message):
    return {"jsonrpc":"2.0","id":msg_id,"error":{"code":code,"message":message}}

def dispatch(message:dict):
    """Return MCP JSON-RPC response for requests; None for notifications."""
    if not isinstance(message,dict) or message.get("jsonrpc")!="2.0" or not isinstance(message.get("method"),str):
        return rpc_error(message.get("id") if isinstance(message,dict) else None,-32600,"Invalid Request")
    method=message["method"];id_present="id" in message;msgid=message.get("id")
    if not id_present:
        # Notifications have no id and MUST NOT be acknowledged.
        return None
    if method=="initialize":
        params=message.get("params") or {}
        requested=params.get("protocolVersion") if isinstance(params,dict) else None
        version=requested if requested in SUPPORTED else PROTOCOL
        result={
          "protocolVersion":version,
          "capabilities":{"tools":{"listChanged":False}},
          "serverInfo":{"name":"adhd-paper-visuals","title":"ADHD Paper Visual Tools","version":__version__},
          "instructions":"Render diagrams from verified paper facts. Inputs must state sources and uncertainty. All tools return true PNG images. No filesystem or network access."
        }
    elif method=="ping":
        result={}
    elif method=="tools/list":
        result={"tools":catalog()}
    elif method=="tools/call":
        params=message.get("params") or {}
        if not isinstance(params,dict):
            return rpc_error(msgid,-32602,"params must be an object")
        name=params.get("name")
        if not isinstance(name,str) or name not in TOOLS:
            return rpc_error(msgid,-32602,"Unknown tool name")
        args=params.get("arguments",{})
        if not isinstance(args,dict):
            return rpc_error(msgid,-32602,"tool arguments must be an object")
        result=render_tool(name,args)
    else:
        return rpc_error(msgid,-32601,"Method not found: "+method)
    return {"jsonrpc":"2.0","id":msgid,"result":result}

def _write_message(payload:dict):
    """Write one complete JSON-RPC line, including with non-blocking host pipes.

    Some IDE/notebook launchers inherit O_NONBLOCK stdout. A single oversized
    sys.stdout.write() would otherwise raise EAGAIN midway through image base64.
    """
    data=(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
    fd=sys.stdout.fileno()
    pos=0
    while pos<len(data):
        try:
            written=os.write(fd,data[pos:pos+32768])
            if written==0:raise BrokenPipeError("stdout closed")
            pos+=written
        except BlockingIOError:
            time.sleep(0.004)
        except InterruptedError:
            continue

def main():
    # Stream framing: one UTF-8 JSON-RPC message per line. No stdout logs.
    try:
        for raw in sys.stdin.buffer:
            if len(raw)>MAX_INPUT_BYTES:
                resp=rpc_error(None,-32600,"Message too large")
            else:
                try:
                    request=json.loads(raw.decode("utf-8"))
                    if isinstance(request,list):
                        resp=rpc_error(None,-32600,"Batch requests not supported by this MCP server")
                    else:
                        resp=dispatch(request)
                except (json.JSONDecodeError,UnicodeDecodeError):
                    resp=rpc_error(None,-32700,"Parse error")
                except Exception as exc:
                    logger.exception("MCP handler failed")
                    resp=rpc_error(None,-32603,"Internal error")
            if resp is not None:
                _write_message(resp)
    except (BrokenPipeError,KeyboardInterrupt):
        return

if __name__=="__main__":
    main()
