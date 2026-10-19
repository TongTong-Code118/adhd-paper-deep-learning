"""Pure, deterministic diagram rendering into PNG using Pillow.

- No browser, font downloads, remote calls, file writes, or executable code.
- Inputs are display strings, not paper-verified facts; the agent must ground them.
- All diagrams return an actual image/png for MCP ImageContent.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import os
from typing import Any

from PIL import Image, ImageDraw, ImageFont

INK="#24424D"
SECONDARY="#536B76"
TEAL="#27877D"
AQUA="#E5F2EF"
CORAL="#D47C56"
CREAM="#F8F6F1"
WHITE="#FFFFFF"
SAND="#F0E9DB"
BORDER="#D5DFDC"
WARN="#FFF1E6"
SHADOW="#E7EAE3"

_FONTS=[
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]
_FONT_BOLD=[
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
]

@lru_cache(maxsize=1)
def font_path(bold:bool=False) -> str:
    env=os.environ.get("ADHD_PAPER_FONT_BOLD" if bold else "ADHD_PAPER_FONT","")
    if env and Path(env).is_file():
        return env
    candidates=(_FONT_BOLD if bold else _FONTS)+_FONTS
    for item in candidates:
        if Path(item).is_file():
            return item
    # Do not silently return tofu squares for Chinese, as that violates the visual contract.
    raise RuntimeError(
      "没有找到可显示中文的本机字体。请安装 Noto Sans CJK / 微软雅黑 / 苹方，"
      "或通过环境变量 ADHD_PAPER_FONT 指向已安装的 CJK 字体文件。"
    )

@lru_cache(maxsize=30)
def font(sz:int,bold:bool=False):
    return ImageFont.truetype(font_path(bold),sz)

class Board:
    def __init__(self,width:int,height:int):
        self.w=width;self.h=height
        self.im=Image.new("RGB",(width,height),CREAM)
        self.d=ImageDraw.Draw(self.im)
        self.d.rounded_rectangle((0,0,width-1,height-1),radius=25,outline=BORDER,width=1)
    def r(self,xy,fill=WHITE,r=20,outline=BORDER,width=1):
        self.d.rounded_rectangle(tuple(map(int,xy)),radius=r,fill=fill,outline=outline,width=width)
    def t(self,x,y,s,size=24,color=INK,bold=False,anchor="la"):
        self.d.text((x,y),str(s),font=font(size,bold),fill=color,anchor=anchor)
    def bbox(self,s,sz,bold=False):
        return self.d.textbbox((0,0),str(s),font=font(sz,bold))
    def tw(self,s,sz,bold=False):
        b=self.bbox(s,sz,bold);return b[2]-b[0]
    def lines(self,s,maxwidth,size,maxlines=3,bold=False):
        # Greedy glyph-aware wrap; do not hide or truncate paper facts.
        result=[]
        for part in str(s).replace("\\r","").split("\\n"):
            if part=="":
                result.append("");continue
            acc=""
            for char in part:
                if acc and self.tw(acc+char,size,bold)>maxwidth:
                    result.append(acc);acc=char
                else: acc+=char
            if acc:result.append(acc)
        if len(result)>maxlines:
            raise ValueError("图内文字过长：请拆图或把节点标题改短，而不是缩小文字到无法阅读。")
        return result
    def paragraph(self,x,y,s,maxw,sz=20,gap=8,limit=3,color=SECONDARY,bold=False):
        ln=self.lines(s,maxw,sz,limit,bold)
        step=sz+gap
        for i,a in enumerate(ln):self.t(x,y+i*step,a,sz,color,bold)
        return len(ln)*step
    def arrow(self,start,end,label="",color=TEAL):
        x1,y1=start;x2,y2=end
        self.d.line((x1,y1,x2,y2),fill=color,width=4,joint="curve")
        if abs(x2-x1)>abs(y2-y1):
            sign=1 if x2>x1 else -1
            self.d.line((x2-13*sign,y2-8,x2,y2,x2-13*sign,y2+8),fill=color,width=4,joint="curve")
        else:
            sign=1 if y2>y1 else -1
            self.d.line((x2-8,y2-13*sign,x2,y2,x2+8,y2-13*sign),fill=color,width=4,joint="curve")
        if label:
            if abs(x2-x1)>abs(y2-y1):
                center=(x1+x2)/2
                self.t(center,(y1+y2)/2+25,label,15,SECONDARY,True,"ma")
            else:
                self.t(x1+28,(y1+y2)/2,label,16,SECONDARY,True)
    def head(self,kicker,title,subtitle):
        self.t(64,34,kicker,17,TEAL,True)
        title_size=38
        if self.tw(title,title_size,True)>self.w-132:
            title_size=31
        if self.tw(title,title_size,True)>self.w-132:
            title_size=25
        if self.tw(title,title_size,True)>self.w-132:
            raise ValueError("标题过长：请精简图标题，把详细说明放到正文。")
        self.t(64,77,title,title_size,INK,True)
        self.paragraph(64,139,subtitle,self.w-140,18,5,2,SECONDARY)
        self.d.line((64,201,self.w-64,201),fill=BORDER,width=2)
    def notice(self,text,y=None,warning=False):
        y=self.h-124 if y is None else y
        self.r((64,y,self.w-64,y+76),WARN if warning else SAND,15,None,0)
        self.t(89,y+11,"证据与边界" if warning else "阅读定位",17,CORAL if warning else TEAL,True)
        self.paragraph(89,y+37,text,self.w-188,16,3,2,INK)
    def output(self):
        buf=BytesIO()
        self.im.save(buf,format="PNG",optimize=True)
        return buf.getvalue()

def _small_node(b,x,y,w,h,num,title,detail,role,focus):
    b.r((x,y,x+w,y+h), AQUA if focus else WHITE,18,TEAL if focus else BORDER,3 if focus else 2)
    b.r((x+22,y+20,x+82,y+62),TEAL if focus else SAND,12,None,0)
    b.t(x+52,y+40,f"{num:02d}",19,WHITE if focus else INK,True,"mm")
    b.paragraph(x+22,y+90,title,w-44,25,8,2,INK,True)
    b.paragraph(x+22,y+174,detail,w-44,18,8,3,SECONDARY)
    b.d.line((x+22,y+h-54,x+w-22,y+h-54),fill=BORDER,width=2)
    b.paragraph(x+22,y+h-44,role,w-44,15,6,2,TEAL if focus else SECONDARY,True)

def flow_diagram(title:str,subtitle:str, nodes:list[dict],relationships:list[str],
                 current:int,source_note:str,kind:str="paper") -> bytes:
    n=len(nodes)
    if not 2<=n<=7: raise ValueError("流程图必须有 2–7 个清晰节点")
    if len(relationships)!=n-1: raise ValueError("关系标签数量必须比节点数量少一")
    if not 0<=current<n: raise ValueError("当前节点索引超出范围")
    # For 5-7 nodes, vertical layout preserves legibility without a horizontal text wall.
    if n>=5:
        h=398+n*154+(n-1)*30
        b=Board(1400,h)
        b.head("PAPER GPS  /  VISUAL-FIRST",title,subtitle)
        y=232
        for i,item in enumerate(nodes):
            active=i==current
            b.r((94,y,1306,y+154), AQUA if active else WHITE,18,TEAL if active else BORDER,3 if active else 2)
            b.r((116,y+18,179,y+60),TEAL if active else SAND,12,None,0)
            b.t(148,y+40,f"{i+1:02d}",18,WHITE if active else INK,True,"mm")
            b.paragraph(211,y+15,item["title"],650,27,6,2,INK,True)
            b.paragraph(211,y+84,item["detail"],870,19,6,2,SECONDARY)
            b.paragraph(1080,y+100,item["role"],190,16,5,2,TEAL if active else SECONDARY,True)
            if i<n-1:
                b.arrow((650,y+158),(650,y+182),relationships[i])
            y+=184
    else:
        b=Board(1400,760)
        b.head("PAPER GPS  /  VISUAL-FIRST",title,subtitle)
        pad=64
        gap=64
        w=(1400-2*pad-gap*(n-1))//n
        if w<205: raise ValueError("节点过多；请按章节分层绘图")
        y=235
        for i,item in enumerate(nodes):
            x=pad+i*(w+gap)
            _small_node(b,x,y,w,315,i+1,item["title"],item["detail"],item["role"],i==current)
            if i<n-1:
                b.arrow((x+w+8,y+158),(x+w+gap-9,y+158),color=TEAL)
                b.t(x+w+gap/2,y+347,relationships[i],14,SECONDARY,True,"ma")
    b.notice(source_note,warning=True)
    return b.output()

def concept_diagram(data:dict) -> bytes:
    b=Board(1400,890)
    b.head("CONCEPT / FOUR STEPS",data["concept"],"先有直觉，再看真实机制；类比必须有映射和失效边界")
    b.r((64,235,650,480),WHITE,20,BORDER,2)
    b.r((750,235,1336,480),AQUA,20,TEAL,2)
    b.t(94,263,"01 生活类比",23,TEAL,True)
    b.paragraph(94,315,data["everyday_analogy"],520,22,12,4,INK,True)
    b.t(780,263,"02 真实机制",23,TEAL,True)
    for i,step in enumerate(data["mechanism_steps"][:4]):
        cy=318+i*37
        b.r((784,cy,817,cy+29),SAND,9,None,0)
        b.t(800,cy+14,str(i+1),14,INK,True,"mm")
        b.paragraph(835,cy,step,445,19,5,1,INK)
    b.arrow((668,352),(728,352),"对应",TEAL)
    y=502
    b.t(70,y,"映射：现实物件 ↔ 学术变量",22,INK,True)
    for i,item in enumerate(data["mappings"][:3]):
        y0=546+i*57
        b.r((76,y0,1324,y0+47), WHITE if i%2==0 else SAND,11,None,0)
        b.t(103,y0+11,item["everyday"],19,INK,True)
        b.t(575,y0+11,"↔",23,TEAL,True)
        b.t(641,y0+11,item["academic"],19,INK,True)
        b.paragraph(965,y0+12,item.get("relationship",""),320,16,4,1,SECONDARY)
    b.r((64,730,1336,808),WARN,15,None,0)
    b.t(88,744,"03 具体例子",18,CORAL,True)
    b.paragraph(244,744,data["numeric_example"],1020,17,5,2,INK)
    b.notice("04 类比失效：" + data["analogy_limit"] + "  ｜  " +data["source_note"],
             y=810, warning=True)
    return b.output()

def formula_diagram(data:dict) -> bytes:
    b=Board(1400,840)
    b.head("EQUATION / VARIABLE LENS",data["title"],"先明确符号和变量依赖，再逐步演算；不能跳过成立条件")
    b.r((64,230,1336,320),AQUA,16,TEAL,2)
    b.t(91,251,"公式",18,TEAL,True)
    b.paragraph(200,246,data["formula"],1090,32,9,2,INK,True)
    b.t(67,357,"👀 变量与单位" if False else "01 变量与单位",23,INK,True)
    syms=data["symbols"][:4]
    for i,s in enumerate(syms):
        x=64+(i*322)
        b.r((x,397,x+300,515),WHITE,16,BORDER,2)
        b.t(x+21,412,s["symbol"],25,TEAL,True)
        b.paragraph(x+21,450,s["meaning"],260,17,5,2,INK)
        unit=s.get("unit","")
        if unit: b.t(x+21,493,"单位："+unit,14,SECONDARY)
    b.t(67,548,"02 推导／运算步骤",23,INK,True)
    steplen=len(data["steps"])
    for i,item in enumerate(data["steps"]):
        x=64+i*(1272//steplen)
        w=1272//steplen-20
        b.r((x,584,x+w,659),AQUA if i==steplen-1 else WHITE,12,BORDER,1)
        b.paragraph(x+12,596,item,w-24,16,6,2,INK,True)
        if i<steplen-1:
            b.arrow((x+w+2,619),(x+w+18,619),color=TEAL)
    b.r((64,676,1336,748),SAND,12,None,0)
    b.t(85,687,"03 数字验算",17,TEAL,True)
    b.paragraph(260,689,data["numeric_example"],1018,17,6,2,INK)
    b.notice("04 边界：" +data["limitation"] +"  ｜  "+data["source_note"],
             y=754,warning=True)
    return b.output()

def prism_diagram(data:dict) -> bytes:
    b=Board(1400,750)
    b.head("FIGURE / TABLE LENS",data["title"],"每个数字都要经过三问：看哪里、说明什么、不能说明什么")
    blocks=[
        ("01 看哪里",data["look_at"],WHITE,TEAL),
        ("02 说明什么",data["supports"],AQUA,TEAL),
        ("03 不能说明什么",data["cannot_conclude"],WARN,CORAL),
    ]
    for i,(heading,body,bg,c) in enumerate(blocks):
        x=64+i*440
        b.r((x,237,x+398,597),bg,20,BORDER,2)
        b.r((x+21,260,x+70,309),c,12,None,0)
        b.t(x+45,284,str(i+1).zfill(2),18,WHITE,True,"mm")
        b.t(x+22,334,heading,27,INK,True)
        b.paragraph(x+22,394,body,352,21,13,6,INK)
    b.notice(data["source_note"],y=631,warning=True)
    return b.output()

def build_png(kind:str, args:dict) -> bytes:
    if kind=="render_paper_map":
        return flow_diagram(args["title"],args["subtitle"],args["nodes"],
                           args["relationships"],args.get("current_index",0),
                           args["source_note"])
    if kind=="render_section_flow":
        stages=[{"title":o["title"],"detail":o["question"],"role":o["purpose"]} for o in args["stages"]]
        return flow_diagram(args["section_title"],"进入本节前：先看依赖，再看细节",
                           stages,args["relationships"],args.get("current_index",0),
                           args["source_note"],"section")
    if kind=="render_concept_diagram":
        return concept_diagram(args)
    if kind=="render_formula_structure":
        return formula_diagram(args)
    if kind=="render_evidence_prism":
        return prism_diagram(args)
    raise ValueError("unknown diagram type")
