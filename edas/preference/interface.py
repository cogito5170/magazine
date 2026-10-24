"""Self-contained HTML A/B rating page for counterfactual manifests.

Left/right placement is randomised per pair and recorded.  Each criterion is
asked separately with A / B / tie / cannot judge.  Answers are kept in the
browser and exported as a JSON list of ``Judgment`` records, which
``edas prefs import`` appends to the judgment store.
"""
from __future__ import annotations

import base64
import html
import io
import json
import os
import random

from .schema import CRITERIA


def build_ab_page(manifest_path: str, out_html: str, page_id: str = "", project_id: str = "",
                  target_style: str = "", seed: int = 0, max_px: int = 1100) -> str:
    with open(manifest_path, encoding="utf-8") as fh:
        man = json.load(fh)
    base = os.path.dirname(manifest_path)
    exp = man["experiment"]
    crit = [c for c, v in CRITERIA.items() if exp in v["experiments"]]
    stim = {s["stimulus_id"]: s for s in man["stimuli"]}
    rng = random.Random(seed)
    images = {}

    def embed(sid):
        if sid not in images:   # each stimulus embedded once, downscaled for screen display
            from PIL import Image
            im = Image.open(os.path.join(base, stim[sid]["file"])).convert("RGB")
            im.thumbnail((max_px, max_px), Image.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=92)
            images[sid] = base64.b64encode(bio.getvalue()).decode()
        return sid

    pairs = []
    for p in man["pairs"]:
        a, b = stim[p["a"]], stim[p["b"]]
        pairs.append({"a": embed(a["stimulus_id"]), "b": embed(b["stimulus_id"]), "font_a": a["font"],
                      "font_b": b["font"], "left": rng.choice(["A", "B"])})
    meta = {"experiment": exp, "page_id": page_id, "project_id": project_id, "target_style": target_style,
            "rendering": man.get("conditions", {}), "criteria": {c: CRITERIA[c] for c in crit}}
    doc = (TEMPLATE.replace("__PAIRS__", json.dumps(pairs)).replace("__IMAGES__", json.dumps(images))
           .replace("__META__", json.dumps(meta, ensure_ascii=False)))
    doc = doc.replace("__TITLE__", html.escape(f"A/B {exp} — {man.get('word') or man.get('text', '')}"))
    with open(out_html, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return out_html


TEMPLATE = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#fafaf8;--fg:#1c1c1a;--muted:#6b6b66;--line:#d9d8d2;--acc:#2f5d8a}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--muted:#a3a29b;--line:#3a3935;--acc:#8fb4dc}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
.pair{border-top:1px solid var(--line);padding:16px 0}
.imgs{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.imgs figure{margin:0}.imgs img{width:100%;border:1px solid var(--line);cursor:zoom-in;background:#fff}
figcaption{font-weight:600;margin-bottom:4px}
.q{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin:6px 0}
.q span{min-width:280px}
.note{color:var(--muted);font-size:13px}
#zoom{position:fixed;inset:0;background:rgba(0,0,0,.85);display:none;align-items:center;justify-content:center}
#zoom img{max-width:96vw;max-height:96vh;background:#fff}
button{font:inherit;padding:6px 12px;border:1px solid var(--line);background:transparent;color:var(--fg);border-radius:6px;cursor:pointer}
@media (max-width:640px){.imgs{grid-template-columns:1fr}.q span{min-width:0;width:100%}}
</style></head><body><main>
<h1>__TITLE__</h1>
<p class="note">Names (fonts, drafts) are hidden. Left/right order is randomised. Answer each question independently;
"tie" and "cannot judge" are valid answers. 서체명·시안명은 숨겨져 있으며 좌우 배치는 무작위입니다.</p>
<label>Rater ID / 평가자 ID <input id="rater" required></label>
<div id="pairs"></div>
<p><button id="export">Export JSON</button> <span class="note" id="status"></span></p>
</main><div id="zoom"><img alt=""></div>
<script>
const PAIRS=__PAIRS__, IMAGES=__IMAGES__, META=__META__;
const key="edas-ab-"+META.experiment+"-"+META.page_id;
let saved={};try{saved=JSON.parse(localStorage.getItem(key)||"{}")}catch(e){}
const root=document.getElementById("pairs"), t0={};
PAIRS.forEach((p,i)=>{
  const ia=IMAGES[p.a], ib=IMAGES[p.b];
  const L=p.left==="A"?["A",ia]:["B",ib], Rr=p.left==="A"?["B",ib]:["A",ia];
  const d=document.createElement("section");d.className="pair";
  d.innerHTML=`<div class="imgs"><figure><figcaption>Left</figcaption><img src="data:image/jpeg;base64,${L[1]}" alt="left stimulus"></figure>
  <figure><figcaption>Right</figcaption><img src="data:image/jpeg;base64,${Rr[1]}" alt="right stimulus"></figure></div>`;
  Object.entries(META.criteria).forEach(([c,v])=>{
    const q=document.createElement("div");q.className="q";
    q.innerHTML=`<span>${v.ko}<br><small class="note">${v.en}</small></span>`+
      [["left","Left"],["right","Right"],["tie","Tie / 동점"],["cannot_judge","Cannot judge / 판단 불가"]].map(([val,lab])=>
      `<label><input type="radio" name="p${i}-${c}" value="${val}"> ${lab}</label>`).join(" ");
    q.addEventListener("change",e=>{saved[`${i}|${c}`]={v:e.target.value,ms:Date.now()-(t0[i]||Date.now())};
      try{localStorage.setItem(key,JSON.stringify(saved))}catch(err){}});
    const prev=saved[`${i}|${c}`]; if(prev){const r=q.querySelector(`input[value="${prev.v}"]`); if(r) r.checked=true;}
    d.appendChild(q);});
  t0[i]=Date.now(); root.appendChild(d);});
document.querySelectorAll(".imgs img").forEach(im=>im.onclick=()=>{const z=document.getElementById("zoom");z.querySelector("img").src=im.src;z.style.display="flex"});
document.getElementById("zoom").onclick=e=>e.currentTarget.style.display="none";
document.getElementById("export").onclick=()=>{
  const rater=document.getElementById("rater").value.trim();
  if(!rater){document.getElementById("status").textContent="Rater ID required";return}
  const out=[];
  Object.entries(saved).forEach(([k,v])=>{const [i,c]=k.split("|");const p=PAIRS[+i];
    let choice=v.v; if(choice==="left") choice=p.left; else if(choice==="right") choice=(p.left==="A"?"B":"A");
    out.push({rater_id:rater,experiment:META.experiment,criterion:c,stimulus_a:p.a,stimulus_b:p.b,choice,
      font_a:p.font_a,font_b:p.font_b,page_id:META.page_id||null,project_id:META.project_id||null,
      target_style:META.target_style||null,presented_left:p.left,rendering:META.rendering,response_ms:v.ms,
      timestamp:new Date().toISOString()});});
  const blob=new Blob([JSON.stringify(out,null,1)],{type:"application/json"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`judgments-${rater}-${META.experiment}.json`;a.click();
  document.getElementById("status").textContent=out.length+" answers exported";};
</script></body></html>"""
