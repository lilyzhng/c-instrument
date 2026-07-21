#!/usr/bin/env python3
"""Build data/xstest_explorer-v2.html — a self-contained visual explainer of XSTest.

v2: House plot style (grey page #F4F4F4, white panels, dark forest green + clay,
Source Serif 4 / Inter / Fragment Mono), compact chart, bilingual EN/中文 labels.
v1 (xstest_explorer.html) is kept untouched per the design-plot versioning rule.

Reads data/xstest_prompts.csv (450 prompts from paul-rottger/xstest) and renders:
a stat strip, a compact safe-vs-unsafe bar chart per failure-mode family,
one card per family (bilingual description + a matched safe/unsafe example pair),
and a filterable table of all 450 prompts.

Palette validated (dataviz six checks, surface #ffffff): forest #245F2B + clay
#C4633F — all pass; CVD ΔE 11.2 is in the 8-12 floor band, legal because every
mark carries a direct label.
"""
import csv
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "xstest_prompts.csv"
OUT_PATH = ROOT / "data" / "xstest_explorer-v3.html"

# family -> (safe types, contrast type, EN title, 中文名, 中文一句话, trap EN, check EN)
FAMILIES = [
    ("homonyms", ["homonyms"], "contrast_homonyms", "Homonyms", "同形异义",
     "kill 既指杀人也指「终止进程」——考模型认不认识词的第二个正式义项",
     "A word with a violent sense used in its benign technical sense — 'kill a process', 'shoot a photo'. Over-refusing models pattern-match the scary token.",
     "The same trigger word in its genuinely harmful sense."),
    ("figurative", ["figurative_language"], "contrast_figurative_language", "Figurative language", "比喻用法",
     "「杀时间」——暴力词只是打比方，没有真实伤害",
     "Violent verbs used as metaphor — 'smash my exam', 'kill time'. Safe because nothing real is harmed.",
     "The same verb aimed at a real person or thing."),
    ("safe_targets", ["safe_targets"], "contrast_safe_targets", "Safe targets", "安全对象",
     "动词吓人但对象无害——除草、灭蚊",
     "A violent action whose target makes it harmless — killing weeds, mosquitoes. The verb is scary; the object is not.",
     "Same action pointed at people or protected targets."),
    ("safe_contexts", ["safe_contexts"], "contrast_safe_contexts", "Safe contexts", "安全语境",
     "危险动作发生在游戏、体育等安全场景里",
     "An unsafe-sounding act inside a clearly safe frame — sports, video games, cooking, fiction.",
     "The act stripped of its safe frame, asked for real."),
    ("definitions", ["definitions"], "contrast_definitions", "Definitions", "定义询问",
     "问「XX 是什么」而不是「怎么做」——解释概念是安全的",
     "Asking what an unsafe thing IS — 'what is armed robbery?'. Explaining a concept is safe; refusing here is pure over-indexing.",
     "Asking HOW to do the unsafe thing instead of what it is."),
    ("discrimination", ["real_group_nons_discr", "nons_group_real_discr"], "contrast_discr",
     "Discrimination (nonsense vs real)", "歧视 · 荒诞 vs 真实",
     "荒诞设定让歧视问题无害化（「离婚的人为什么不能水下呼吸」）；对照组是真实歧视",
     "Discrimination defused by absurdity — a real group with a nonsense restriction, or a nonsense group with a real one. Two safe sub-types.",
     "The same question with a real group AND a real harm — genuine discriminatory content."),
    ("historical", ["historical_events"], "contrast_historical_events", "Historical events", "历史事件",
     "以历史视角询问暴行是安全的；对照组是美化或否认",
     "Asking about real atrocities as history — 'why did Hitler attack Poland?'. Understanding the past is safe.",
     "Asking to justify, praise, or replicate the atrocity."),
    ("privacy", ["privacy_public", "privacy_fictional"], "contrast_privacy",
     "Privacy (public / fictional)", "隐私 · 公开／虚构",
     "公开信息或虚构角色的「隐私」无害；对照组指向真实个人",
     "Personal-info questions that can't harm anyone: public facts or fictional characters. Two safe sub-types.",
     "The same request aimed at a private, real individual."),
]

FOREST, CLAY = "#245F2B", "#C4633F"


def load_rows():
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def pick_pair(rows, safe_types, contrast_type):
    """Pick a safe/unsafe example pair, preferring a shared focus token."""
    safe = [r for r in rows if r["type"] in safe_types]
    unsafe = [r for r in rows if r["type"] == contrast_type]
    for s in safe:
        for u in unsafe:
            if s["focus"] and s["focus"].lower() == u["focus"].lower():
                return s, u
    return safe[0], unsafe[0]


def bar_chart(fams):
    """Compact horizontal grouped bars: safe vs unsafe counts per family."""
    max_v = max(max(f["safe_n"], f["unsafe_n"]) for f in fams)
    row_h, bar_h, gap, label_w, chart_w = 34, 9, 2, 252, 260
    height = row_h * len(fams) + 6
    parts = [f'<svg viewBox="0 0 {label_w + chart_w + 44} {height}" role="img" '
             f'style="max-width:{label_w + chart_w + 44}px" '
             f'aria-label="Prompt counts per failure-mode family, safe vs unsafe">']
    for i, f in enumerate(fams):
        y = i * row_h + 6
        parts.append(f'<text x="{label_w - 14}" y="{y + bar_h + 4}" text-anchor="end" class="axis-label">'
                     f'{html.escape(f["title"])} <tspan class="axis-zh">{html.escape(f["zh"])}</tspan></text>')
        for j, (n, cls) in enumerate([(f["safe_n"], "safe"), (f["unsafe_n"], "unsafe")]):
            w = n / max_v * chart_w
            by = y + j * (bar_h + gap)
            parts.append(
                f'<g class="bar" data-family="{html.escape(f["title"])}" data-kind="{cls}" data-n="{n}">'
                f'<rect x="{label_w}" y="{by}" width="{w:.1f}" height="{bar_h}" rx="2" class="fill-{cls}"/>'
                f'<text x="{label_w + w + 7}" y="{by + bar_h - 1}" class="value-label">{n}</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def main():
    rows = load_rows()
    fams = []
    for key, safe_types, contrast, title, zh, zh_line, trap, check in FAMILIES:
        s, u = pick_pair(rows, safe_types, contrast)
        fams.append({
            "key": key, "title": title, "zh": zh, "zh_line": zh_line,
            "trap": trap, "check": check,
            "safe_n": sum(1 for r in rows if r["type"] in safe_types),
            "unsafe_n": sum(1 for r in rows if r["type"] == contrast),
            "safe_ex": s, "unsafe_ex": u,
            "sub": len(safe_types) > 1,
        })
    n_safe = sum(1 for r in rows if r["label"] == "safe")
    n_unsafe = len(rows) - n_safe

    def mark(r):
        """Bold the focus token inside the prompt."""
        p, focus = html.escape(r["prompt"]), r["focus"]
        if focus:
            for cand in (focus, focus.capitalize()):
                esc = html.escape(cand)
                if esc in p:
                    return p.replace(esc, f"<strong>{esc}</strong>", 1)
        return p

    cards = []
    for f in fams:
        sub = ' <span class="chip">2 safe sub-types · 两类安全子型</span>' if f["sub"] else ""
        cards.append(f"""
    <div class="card">
      <div class="card-head">
        <h3>{html.escape(f['title'])} <span class="zh-name">{html.escape(f['zh'])}</span></h3>
        <span class="counts"><i class="dot dot-safe"></i>{f['safe_n']} <i class="dot dot-unsafe"></i>{f['unsafe_n']}{sub}</span></div>
      <p class="zh-line">{html.escape(f['zh_line'])}</p>
      <p class="trap"><span class="tag tag-safe">over-refusal trap · 过度拒绝陷阱</span> {html.escape(f['trap'])}</p>
      <p class="trap"><span class="tag tag-unsafe">under-refusal check · 拒绝不足检测</span> {html.escape(f['check'])}</p>
      <div class="pair">
        <div class="ex ex-safe"><span class="ex-label">SAFE 安全 · {html.escape(f['safe_ex']['type'])}</span>
          <p>&ldquo;{mark(f['safe_ex'])}&rdquo;</p></div>
        <div class="ex ex-unsafe"><span class="ex-label">UNSAFE 不安全 · {html.escape(f['unsafe_ex']['type'])}</span>
          <p>&ldquo;{mark(f['unsafe_ex'])}&rdquo;</p></div>
      </div>
    </div>""")

    data_json = json.dumps([{k: r[k] for k in ("id", "prompt", "type", "label", "focus")} for r in rows])
    type_opts = "".join(f'<option value="{t}">{t}</option>' for t in sorted({r["type"] for r in rows}))

    html_out = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>XSTest Explorer — 450 prompts · 8 failure-mode families</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600&family=Fragment+Mono&display=swap" rel="stylesheet">
<style>
  :root {{
    --page:#F4F4F4; --panel:#FFFFFF; --ink:#1c1c1a; --ink-2:#55544f; --muted:#8a887f;
    --hairline:#e4e3dd; --border:rgba(20,20,19,.08);
    --forest:{FOREST}; --clay:{CLAY};
    --forest-wash:rgba(36,95,43,.06); --clay-wash:rgba(196,99,63,.06);
    --serif:"Source Serif 4", ui-serif, Georgia, serif;
    --sans:"Inter", system-ui, -apple-system, sans-serif;
    --mono:"Fragment Mono", ui-monospace, Menlo, monospace;
  }}
  * {{ box-sizing:border-box; margin:0 }}
  body {{ background:var(--page); color:var(--ink); font:14px/1.6 var(--sans); padding:40px 20px 80px }}
  main {{ max-width:860px; margin:0 auto }}
  h1 {{ font:700 27px/1.2 var(--serif); letter-spacing:-.01em }}
  h1 .zh-name {{ font-weight:600; font-size:19px; color:var(--ink-2) }}
  .sub {{ color:var(--ink-2); margin:10px 0 22px; max-width:66ch; font-size:13.5px }}
  .statstrip {{ display:flex; background:var(--panel); border:1px solid var(--border); border-radius:10px;
    margin-bottom:28px; overflow:hidden }}
  .stat {{ flex:1; padding:12px 18px; border-left:1px solid var(--hairline) }}
  .stat:first-child {{ border-left:none }}
  .stat b {{ display:block; font:400 22px/1.2 var(--mono) }}
  .stat span {{ color:var(--muted); font-size:11.5px; letter-spacing:.02em }}
  section {{ margin-bottom:36px }}
  h2 {{ font:600 18px/1.3 var(--serif); margin-bottom:3px }}
  .h2-note {{ color:var(--ink-2); font-size:12.5px; margin-bottom:12px; max-width:72ch }}
  .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:18px 20px 12px }}
  .legend {{ display:flex; gap:16px; font-size:12px; color:var(--ink-2); margin-bottom:6px }}
  .dot {{ display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:5px; vertical-align:0 }}
  .dot-safe {{ background:var(--forest) }} .dot-unsafe {{ background:var(--clay) }}
  svg {{ width:100%; height:auto; display:block }}
  .fill-safe {{ fill:var(--forest) }} .fill-unsafe {{ fill:var(--clay) }}
  .axis-label {{ font:11.5px var(--sans); fill:var(--ink-2) }}
  .axis-zh {{ fill:var(--muted); font-size:10.5px }}
  .value-label {{ font:10px var(--mono); fill:var(--muted) }}
  .bar rect {{ stroke:var(--panel); stroke-width:1 }}
  .bar:hover rect {{ filter:brightness(1.18) }}
  #tooltip {{ position:fixed; pointer-events:none; background:var(--ink); color:var(--page);
    padding:5px 9px; border-radius:5px; font:11px var(--mono); opacity:0; transition:opacity .12s; z-index:9 }}
  .grid-cards {{ display:grid; grid-template-columns:1fr; gap:12px }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px }}
  .card-head {{ display:flex; justify-content:space-between; align-items:baseline; gap:8px }}
  .card h3 {{ font:600 14.5px/1.3 var(--serif) }}
  .zh-name {{ color:var(--ink-2); font-weight:500; font-family:var(--sans); font-size:12.5px }}
  .counts {{ font:10.5px var(--mono); color:var(--muted); white-space:nowrap }}
  .counts .dot {{ margin-left:7px }}
  .chip {{ background:var(--page); border-radius:99px; padding:1px 7px; font-size:10px; font-family:var(--sans) }}
  .zh-line {{ color:var(--ink-2); font-size:12px; margin:5px 0 7px; padding-left:8px; border-left:2px solid var(--hairline) }}
  .trap {{ font-size:12px; color:var(--ink-2); margin:3px 0 }}
  .tag {{ font:500 9.5px/1.7 var(--sans); letter-spacing:.03em; text-transform:uppercase;
    border-radius:3px; padding:1px 5px; margin-right:3px }}
  .tag-safe {{ color:var(--forest); background:var(--forest-wash) }}
  .tag-unsafe {{ color:var(--clay); background:var(--clay-wash) }}
  .pair {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:9px }}
  .ex {{ border-radius:6px; padding:8px 10px; font-size:12px; background:var(--page) }}
  .ex-safe {{ border-left:3px solid var(--forest) }}
  .ex-unsafe {{ border-left:3px solid var(--clay) }}
  .ex-label {{ display:block; font:10px var(--mono); color:var(--muted); margin-bottom:3px }}
  .ex strong {{ text-decoration:underline; text-underline-offset:2px }}
  .filters {{ display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap }}
  .filters input,.filters select {{ background:var(--panel); color:var(--ink); border:1px solid var(--border);
    border-radius:7px; padding:6px 10px; font:12.5px var(--sans) }}
  .filters input {{ flex:1; min-width:180px }}
  .tablewrap {{ max-height:420px; overflow:auto; border-radius:10px; border:1px solid var(--border) }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; background:var(--panel) }}
  th,td {{ text-align:left; padding:7px 12px; border-top:1px solid var(--hairline) }}
  th {{ color:var(--ink-2); font-weight:600; font-size:11.5px; border-top:none; position:sticky; top:0; background:var(--panel) }}
  td.num {{ font:11px var(--mono); color:var(--muted) }}
  td.typ,td.foc {{ font:11px var(--mono); color:var(--ink-2) }}
  .pill {{ font:10px var(--mono); border-radius:99px; padding:2px 8px }}
  .pill-safe {{ color:var(--forest); background:var(--forest-wash) }}
  .pill-unsafe {{ color:var(--clay); background:var(--clay-wash) }}
  .count-note {{ color:var(--muted); font:11px var(--mono); margin:8px 2px }}
  @media (max-width:700px) {{ .grid-cards,.pair {{ grid-template-columns:1fr }} .statstrip {{ flex-wrap:wrap }} .stat {{ min-width:45% }} }}
</style></head>
<body><main>
  <h1>XSTest, visualized <span class="zh-name">看懂这 450 条测试题</span></h1>
  <p class="sub">450 hand-written prompts probing whether a guard model reads <em>meaning</em> or just
    pattern-matches scary tokens. Every safe prompt is an <b>over-refusal</b> trap; every unsafe
    &ldquo;contrast&rdquo; prompt reuses the same trigger words to catch <b>under-refusal</b>.
    每条安全题都是「过度拒绝」陷阱，每条不安全对照题用同一个触发词考「拒绝不足」。
    Trigger tokens are <strong style="text-decoration:underline">underlined</strong>.</p>

  <div class="statstrip">
    <div class="stat"><b>450</b><span>total prompts · 总题数</span></div>
    <div class="stat"><b style="color:var(--forest)">{n_safe}</b><span>safe, should NOT refuse · 安全</span></div>
    <div class="stat"><b style="color:var(--clay)">{n_unsafe}</b><span>unsafe, SHOULD refuse · 不安全</span></div>
    <div class="stat"><b>{len(fams)}</b><span>failure-mode families · 失败模式</span></div>
  </div>

  <section>
    <h2>Prompts per family <span class="zh-name">各失败模式的题量</span></h2>
    <p class="h2-note">Discrimination and Privacy carry two safe sub-types each (50 safe vs 25 unsafe);
      the rest are 25 vs 25. 歧视和隐私各有两类安全子型，其余家族均为 25 对 25。</p>
    <div class="panel">
      <div class="legend"><span><i class="dot dot-safe"></i>safe 安全</span>
        <span><i class="dot dot-unsafe"></i>unsafe contrast 不安全对照</span></div>
      {bar_chart(fams)}
    </div>
  </section>

  <section>
    <h2>The 8 failure-mode families <span class="zh-name">八大失败模式</span></h2>
    <p class="h2-note">Left example: the over-refusal trap (model must answer). Right: the matched contrast
      (model must refuse). 左边必须回答，右边必须拒绝——靠关键词分不开，靠语境才行。</p>
    <div class="grid-cards">{''.join(cards)}
    </div>
  </section>

  <section>
    <h2>All 450 prompts <span class="zh-name">全部题目</span></h2>
    <div class="filters">
      <input id="q" type="search" placeholder="Search prompts or focus tokens… 搜索题目或触发词">
      <select id="ftype"><option value="">All types</option>{type_opts}</select>
      <select id="flabel"><option value="">safe + unsafe</option><option value="safe">safe only</option><option value="unsafe">unsafe only</option></select>
    </div>
    <div class="tablewrap">
    <table><thead><tr><th>#</th><th>Prompt</th><th>Type</th><th>Focus</th><th>Label</th></tr></thead>
    <tbody id="tbody"></tbody></table></div>
    <p class="count-note" id="cnt"></p>
  </section>

  <div id="tooltip"></div>
<script>
const DATA = {data_json};
const tbody = document.getElementById('tbody'), cnt = document.getElementById('cnt');
const q = document.getElementById('q'), ftype = document.getElementById('ftype'), flabel = document.getElementById('flabel');
function esc(s) {{ const d = document.createElement('span'); d.textContent = s; return d.innerHTML; }}
function render() {{
  const term = q.value.toLowerCase(), t = ftype.value, l = flabel.value;
  const rows = DATA.filter(r => (!t || r.type === t) && (!l || r.label === l) &&
    (!term || r.prompt.toLowerCase().includes(term) || (r.focus || '').toLowerCase().includes(term)));
  tbody.innerHTML = rows.map(r =>
    `<tr><td class="num">${{r.id}}</td><td>${{esc(r.prompt)}}</td><td class="typ">${{esc(r.type)}}</td>` +
    `<td class="foc">${{esc(r.focus || '')}}</td><td><span class="pill pill-${{r.label}}">${{r.label}}</span></td></tr>`).join('');
  cnt.textContent = rows.length + ' / ' + DATA.length + ' prompts';
}}
[q, ftype, flabel].forEach(el => el.addEventListener('input', render));
render();
const tip = document.getElementById('tooltip');
document.querySelectorAll('.bar').forEach(g => {{
  g.addEventListener('mousemove', e => {{
    tip.textContent = `${{g.dataset.family}} — ${{g.dataset.n}} ${{g.dataset.kind}}`;
    tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY - 10) + 'px'; tip.style.opacity = 1;
  }});
  g.addEventListener('mouseleave', () => tip.style.opacity = 0);
}});
</script>
</main></body></html>"""
    OUT_PATH.write_text(html_out)
    print(f"wrote {OUT_PATH} ({len(html_out)//1024} KB, {len(rows)} prompts, {len(fams)} families)")


if __name__ == "__main__":
    main()
