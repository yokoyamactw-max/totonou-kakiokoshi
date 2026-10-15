"""書き起こしHTMLから、Obsidian で検索・一覧できる「目次ノート」（同名の .md）を作る。

使い方:
  python3 catalog.py <書き起こし.html> [--out-dir DIR] [--date YYYY-MM-DD] [--kind 講座|会議|音声|まとめ]
                     [--series シリーズ名] [--speaker 講師・主催] [--owner 自分|他人] [--url 元URL] [--tags a,b]

- Obsidian は .html をノートとして扱わないので、HTMLへは wikilink ではなく file:// リンクで飛ぶ
- 目次ノートには、属性（日付・種類・シリーズ・講師など）、HTMLへのリンク、要約、書き起こし本文（スクショ抜き）を入れる
- 本文を入れるのは、Obsidian の検索や Smart Connections が HTML の中身を読まないため
- --out-dir を省くと HTML と同じフォルダに書く。既存の .md は上書きする（手で書き足すなら「## メモ」欄に。ここは引き継ぐ）
"""
import argparse, html, os, pathlib, re, sys, time

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8")
from html.parser import HTMLParser

ap = argparse.ArgumentParser()
ap.add_argument("html_path")
ap.add_argument("--out-dir")
ap.add_argument("--date")
ap.add_argument("--kind", default="講座")
ap.add_argument("--series", default="")
ap.add_argument("--speaker", default="")
ap.add_argument("--owner", default="他人")
ap.add_argument("--url", default="")
ap.add_argument("--tags", default="")
a = ap.parse_args()

src = os.path.abspath(os.path.expanduser(a.html_path))
doc = open(src, encoding="utf-8", errors="ignore").read()
doc = re.sub(r'src="data:[^"]*"', 'src=""', doc)  # 埋め込み画像は読まない


class MD(HTMLParser):
    """build.py の出力（summary / blk）と、ふつうのHTMLの両方を Markdown 風の行にする。"""
    SKIP = {"style", "script", "nav", "figure", "figcaption", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.skip, self.lists = [], [], 0, []
        self.in_raw = 0
        self.cls_stack = []
        self.cell = []
        self.href = None
        self.ncell, self.row_no = 0, 0

    def flush(self, prefix=""):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if t:
            self.out.append(prefix + t)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = d.get("class", "") or ""
        self.cls_stack.append((tag, cls))
        if tag in self.SKIP or tag == "details":
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "p", "li", "div", "tr", "section", "br", "header"):
            self.flush()
        if tag in ("ul", "ol"):
            self.lists.append(tag)
        if tag in ("strong", "b"):
            self.buf.append("**")
        if tag == "a":
            self.href = d.get("href")
        if tag in ("td", "th"):
            self.ncell += 1
        if tag == "tr":
            self.ncell = 0
        if tag == "table":
            self.row_no = 0

    def handle_endtag(self, tag):
        cls = ""
        while self.cls_stack:
            t, c = self.cls_stack.pop()
            if t == tag:
                cls = c
                break
        if tag in self.SKIP or tag == "details":
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("strong", "b"):
            self.buf.append("**")
        elif tag == "a":
            if self.href and self.href.startswith("http"):
                self.buf.append(f"（{self.href}）")
            self.href = None
        elif tag == "h1":
            self.flush("# ")
        elif tag == "h2":
            self.flush("## ")
        elif tag in ("h3", "h4"):
            self.flush("### ")
        elif tag == "li":
            self.flush("  " * max(0, len(self.lists) - 1) + ("1. " if self.lists and self.lists[-1] == "ol" else "- "))
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
        elif tag in ("td", "th"):
            self.buf.append(" | ")
        elif tag == "div" and "time" in cls.split():
            self.flush("### ")
        elif tag == "tr":
            t = re.sub(r"\s+", " ", "".join(self.buf)).strip().rstrip("|").strip()
            self.buf = []
            if t:
                self.out.append("| " + t + " |")
                if self.row_no == 0:
                    self.out.append("|" + " --- |" * max(1, self.ncell))
                self.row_no += 1
        elif tag in ("p", "div", "section", "header"):
            self.flush()

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def convert(fragment):
    p = MD()
    p.feed(fragment)
    p.flush()
    lines, prev = [], None
    for ln in p.out:
        row = ln.startswith("| ") or ln.startswith("| ---") or ln.startswith("|---")
        ln = ln.replace("****", "") if row else ln.replace("****", "").strip(" |")
        if not ln or ln == prev:
            continue
        if row:
            if prev is not None and not prev.startswith("|") and lines and lines[-1] != "":
                lines.append("")
            lines.append(ln)
            prev = ln
            continue
        if prev is not None and prev.startswith("|"):
            lines.append("")
        if ln.startswith("#") and lines:
            lines.append("")
        lines.append(ln)
        if ln.startswith("#"):
            lines.append("")
        elif not ln.startswith(("- ", "1. ", "  ")):
            lines.append("")
        prev = ln
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def grab(pattern):
    m = re.search(pattern, doc, re.S)
    return m.group(1) if m else ""


title = html.unescape(grab(r"<h1[^>]*>(.*?)</h1>") or grab(r"<title>(.*?)</title>"))
title = re.sub(r"<[^>]+>", "", title).strip() or os.path.splitext(os.path.basename(src))[0]
meta_line = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", grab(r'<div class="meta">(.*?)</div>')))).strip()

if 'class="blk"' in doc:  # totonou-kakiokoshi（build.py）形式
    summary_md = convert(grab(r'<div class="summary">(.*?)</div>\s*<h2>'))
    body_start = doc.find('<section class="blk"')
    body_md = convert(doc[body_start:]) if body_start >= 0 else ""
    body_head = "## 書き起こし本文"
else:  # それ以外のHTML（まとめページなど）はページ全体をそのまま変換
    summary_md = ""
    body_md = convert(re.sub(r"<h1[^>]*>.*?</h1>", "", grab(r"<body[^>]*>(.*)</body>") or doc, flags=re.S))
    body_head = "## 本文"

date = a.date
if not date:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", os.path.basename(src)) or re.search(r"(\d{4}-\d{2}-\d{2})", meta_line)
    date = m.group(1) if m else time.strftime("%Y-%m-%d", time.localtime(getattr(os.stat(src), "st_birthtime", os.stat(src).st_mtime)))
length = ""
m = re.search(r"(約?\d+時間\d+分(?:\d+秒)?|約?\d+分(?:\d+秒)?)", meta_line)
if m:
    length = m.group(1)

out_dir = os.path.abspath(os.path.expanduser(a.out_dir)) if a.out_dir else os.path.dirname(src)
os.makedirs(out_dir, exist_ok=True)
stem = os.path.splitext(os.path.basename(src))[0]
md_path = os.path.join(out_dir, stem + ".md")

memo = ""
if os.path.exists(md_path):
    old = open(md_path, encoding="utf-8").read()
    m = re.search(r"\n## メモ\n(.*?)(?=\n## |\Z)", old, re.S)
    memo = m.group(1).strip() if m else ""

html_name = os.path.basename(src)
html_final = os.path.join(out_dir, html_name)
file_url = pathlib.Path(html_final).as_uri()  # Windows でも file:///C:/... になる
tags = ["書き起こし"] + [t.strip() for t in a.tags.split(",") if t.strip()]


def yq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


fm = [
    "---",
    f"タイトル: {yq(title)}",
    f"日付: {date}",
    f"種類: {a.kind}",
    f"シリーズ: {yq(a.series)}",
    f"講師・主催: {yq(a.speaker)}",
    f"素材: {a.owner}",
    f"長さ: {yq(length)}",
    f"元URL: {yq(a.url)}",
    f"HTML: {yq(html_name)}",
    "tags:",
] + [f"  - {t}" for t in tags] + ["---"]

parts = [
    "\n".join(fm),
    f"# {title}",
    f"> {meta_line}" if meta_line else "",
    f"**HTMLを開く**：[ブラウザで開く]({file_url})",
    "## メモ\n\n" + (memo or "（気づき・使いどころをここに書く。目次ノートを作り直しても残る）"),
    "## 要約\n\n" + summary_md if summary_md else "",
    f"{body_head}\n\n{body_md}" if body_md else "",
]
text = "\n\n".join(p for p in parts if p).rstrip() + "\n"
# 要約内の見出しを1段下げる（## 要約 の下に入れるため）
if summary_md:
    head, sep, rest = text.partition("## 要約\n\n")
    summ, sep2, tail = rest.partition(f"\n\n{body_head}")
    summ = re.sub(r"^(#{2,3}) ", lambda m: "#" + m.group(1) + " ", summ, flags=re.M)
    text = head + sep + summ + sep2 + tail
open(md_path, "w", encoding="utf-8").write(text)
print(f"{md_path} chars={len(text)} summary={'yes' if summary_md else 'no'} body_lines={body_md.count(chr(10)) + 1 if body_md else 0}")
