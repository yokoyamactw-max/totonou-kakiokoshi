"""完成したHTMLと途中生成物を機械的に検証する。1つでも NG があれば終了コード1。
使い方: python3 verify.py <workdir> <出力.html>
確認すること
 1. 整形チャンク：全ブロックのキーがそろっているか / 桁の暴走（数字40桁以上） / 同じ語句の5連続
 2. HTML：画像がすべて正しいJPEGか / 全セクションに整形文が入ったか / 要約があるか / 末尾まで書けているか
 3. 文字起こしの末尾が区間の終わりまで届いているか（途中切れ）
"""
import base64, glob, json, os, re, sys

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8")

wd, out = os.path.abspath(sys.argv[1]), sys.argv[2]
ng = []
meta = json.load(open(os.path.join(wd, "meta.json"), encoding="utf-8"))
segs = json.load(open(os.path.join(wd, "transcript.json"), encoding="utf-8"))["segments"]

keys_all = set()
for fi in sorted(glob.glob(os.path.join(wd, "clean", "in_*.json"))):
    n = re.search(r"in_(\d+)\.json", fi).group(1)
    fo = os.path.join(wd, "clean", f"out_{n}.json")
    ins = json.load(open(fi, encoding="utf-8"))
    if not any(b["text"] for b in ins):  # 話し声が無いチャンクは整形不要
        print(f"in_{n}: 発言なし（整形不要）")
        continue
    if not os.path.exists(fo):
        ng.append(f"out_{n}.json がない")
        continue
    o = json.load(open(fo, encoding="utf-8"))
    ik = {str(b["t"]) for b in ins}
    if ik - set(o):
        ng.append(f"out_{n}: 欠けたブロック {sorted(ik - set(o))[:5]}")
    keys_all |= set(o)
    si = "".join(b["text"] for b in ins)
    so = "".join(p for v in o.values() for p in v)
    ratio = len(so) / max(len(si), 1)
    if re.search(r"(?:[0-9],?){40,}", so):
        ng.append(f"out_{n}: 数字の暴走あり")
    if re.search(r"(.{4,40}?)\1{4,}", so):
        ng.append(f"out_{n}: 同じ語句の連続あり")
    note = "  ← 大きく減っている。内容が落ちていないか末尾と数字を確認" if ratio < 0.7 else ""
    print(f"out_{n}: blocks={len(o)} ratio={ratio:.2f}{note}")

s = open(out, encoding="utf-8").read()
imgs = re.findall(r"base64,([A-Za-z0-9+/=]+)", s)
bad = sum(1 for x in imgs if base64.b64decode(x)[:2] != b"\xff\xd8")
ids = set(re.findall(r'id="t(\d+)"', s))
if bad:
    ng.append(f"壊れた画像 {bad} 枚")
if keys_all and ids - keys_all:
    empty = [i for i in ids - keys_all]
    print(f"整形文なしのセクション {len(empty)}（発言がない区間なら問題なし）")
if not s.rstrip().endswith("</html>"):
    ng.append("HTMLが末尾まで書けていない")
if "<h2>" not in s.split('<div class="summary">', 1)[-1][:200]:
    print("注意: 要約（summary.html）が入っていない")
if segs and segs[-1]["end"] + 60 < float(meta["end"]):
    print(f"注意: 文字起こしが {segs[-1]['end']:.0f}s で終わっている（区間の終わり {meta['end']:.0f}s）。"
          "無音なら問題なし、音声があるなら途中切れ")
print(f"images={len(imgs)} sections={len(ids)} MB={len(s.encode()) / 1e6:.1f}")
if ng:
    print("NG:", *ng, sep="\n - ")
    sys.exit(1)
print("OK")
