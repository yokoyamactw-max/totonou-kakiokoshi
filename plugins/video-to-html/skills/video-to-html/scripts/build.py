"""1本ぶんのHTMLを組み立てる。スクショは base64 で埋め込み、ファイル単体で開ける。
使い方: python3 build.py <workdir> <出力.html> "<タイトル>" "<メタ行>"
読むもの: summary.html（任意）/ clean/out_N.json（整形文。控えの out_N_pass1.json 等は読まない）
"""
import base64, glob, html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blocks

wd, out, title, meta_line = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
meta, segs, shots = blocks.load(wd)
gs = blocks.groups(meta, shots)
raws = blocks.texts(gs, segs)
sp = os.path.join(wd, "summary.html")
summary = open(sp).read() if os.path.exists(sp) else ""
cleaned = {}
for f in sorted(glob.glob(os.path.join(wd, "clean", "out_*.json"))):
    if re.fullmatch(r"out_\d+\.json", os.path.basename(f)):
        cleaned.update({int(k): v for k, v in json.load(open(f)).items()})

sections = []
for g, raw in zip(gs, raws):
    t = g[0][0]
    imgs = []
    for st, p in g:
        if p is None:
            continue
        b64 = base64.b64encode(open(p, "rb").read()).decode()
        cap = f"<figcaption>{blocks.ts(st)}</figcaption>" if len(g) > 1 else ""
        imgs.append(f'<figure><img loading="lazy" src="data:image/jpeg;base64,{b64}" alt="{blocks.ts(st)}の画面">{cap}</figure>')
    img = f'<div class="grid n{min(len(imgs), 2)}">{"".join(imgs)}</div>' if imgs else ""
    paras = cleaned.get(int(t))
    if paras:
        body = "".join(f"<p>{html.escape(x)}</p>" for x in paras)
        body += f'<details><summary>元の書き起こし</summary><p class="raw">{html.escape(raw)}</p></details>'
    else:
        body = f'<p>{html.escape(raw) or "（発言なし）"}</p>'
    sections.append(f'<section class="blk" id="t{int(t)}"><div class="time">{blocks.ts(t)}</div>{img}{body}</section>')

toc = "".join(f'<a href="#t{int(g[0][0])}">{blocks.ts(g[0][0])}</a>' for g in gs)
heading = "スクリーンショット＋書き起こし" if shots else "書き起こし"
page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1f;--sub:#555;--line:#e3e0d8;--acc:#9a3b1f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#161615;--fg:#ecebe6;--sub:#b5b3ab;--line:#33322e;--acc:#e08a6a}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:17px/1.9 "Hiragino Sans",system-ui,sans-serif}}
main{{max-width:860px;margin:0 auto;padding:32px 20px 80px}}
h1{{font-size:1.6rem;line-height:1.4;margin:0 0 4px}} h2{{font-size:1.25rem;margin:40px 0 12px;border-bottom:2px solid var(--acc);padding-bottom:4px}}
.meta{{color:var(--sub);font-size:.9rem}}
.summary{{border:1px solid var(--line);border-radius:10px;padding:8px 24px;margin-top:24px}}
.toc{{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:.85rem}} .toc a{{color:var(--acc)}}
.blk{{border-top:1px solid var(--line);padding:24px 0}}
.time{{font-weight:700;color:var(--acc);font-variant-numeric:tabular-nums;margin-bottom:8px}}
.blk img{{width:100%;border-radius:8px;border:1px solid var(--line);display:block}}
.grid{{display:grid;gap:8px}} .grid.n2{{grid-template-columns:1fr 1fr}}
.grid figure{{margin:0}} .grid figcaption{{font-size:.75rem;color:var(--sub);font-variant-numeric:tabular-nums}}
.blk p{{margin:14px 0 0}}
.blk details{{margin-top:12px;font-size:.85rem;color:var(--sub)}} .blk summary{{cursor:pointer}}
.blk .raw{{white-space:pre-wrap;margin-top:6px}}
@media print{{.blk details{{display:none}}}}
</style></head><body><main>
<h1>{html.escape(title)}</h1>
<div class="meta">{html.escape(meta_line)}</div>
<div class="summary">{summary}</div>
<h2>目次</h2><nav class="toc">{toc}</nav>
<h2>{heading}</h2>
{''.join(sections)}
</main></body></html>"""
open(out, "w").write(page)
print(f"{out} blocks={len(sections)} shots={len(shots)} MB={len(page.encode()) / 1e6:.1f}")
