"""マニュアルサイト（Cloudflare Pages）を public/ に組み立てる。
使い方: python3 site/build.py
- 版番号は plugins/totonou-kakiokoshi/.claude-plugin/plugin.json から読む
- スキルの zip を2つ作る：版付き（totonou-kakiokoshi-v1.2.0.zip）と、いつも最新の固定名（totonou-kakiokoshi.zip）
  同じ zip を dist/ にも置く（GitHub のリリースに添付する用）
- 公開は: npx wrangler@latest pages deploy site/public --project-name totonou-kakiokoshi --branch main
"""
import datetime, json, os, shutil, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
PUB = os.path.join(SITE, "public")
SKILL = os.path.join(ROOT, "plugins", "totonou-kakiokoshi", "skills", "totonou-kakiokoshi")
VERSION = json.load(open(os.path.join(ROOT, "plugins", "totonou-kakiokoshi", ".claude-plugin", "plugin.json"),
                         encoding="utf-8"))["version"]
UPDATED = datetime.date.today().isoformat()
ZIP = f"totonou-kakiokoshi-v{VERSION}.zip"


def make_zip(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("README.md", "LICENSE"):
            z.write(os.path.join(ROOT, name), name)
        for base, dirs, files in os.walk(SKILL):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for f in sorted(files):
                if f == ".DS_Store" or f.endswith(".pyc"):
                    continue
                full = os.path.join(base, f)
                z.write(full, os.path.join("totonou-kakiokoshi", os.path.relpath(full, SKILL)))


shutil.rmtree(PUB, ignore_errors=True)
os.makedirs(PUB)
shutil.copytree(os.path.join(SITE, "assets"), os.path.join(PUB, "assets"))
page = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
page = page.replace("{{VERSION}}", VERSION).replace("{{UPDATED}}", UPDATED).replace("{{ZIP}}", ZIP)
assert "{{" not in page, "置き換え忘れ"
open(os.path.join(PUB, "index.html"), "w", encoding="utf-8").write(page)
open(os.path.join(PUB, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")
open(os.path.join(PUB, "_headers"), "w").write(
    "/*\n  X-Robots-Tag: noindex, nofollow\n"
    "/*.zip\n  Cache-Control: no-cache\n")

make_zip(os.path.join(PUB, ZIP))
shutil.copyfile(os.path.join(PUB, ZIP), os.path.join(PUB, "totonou-kakiokoshi.zip"))
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
shutil.copyfile(os.path.join(PUB, ZIP), os.path.join(ROOT, "dist", ZIP))

with zipfile.ZipFile(os.path.join(PUB, ZIP)) as z:
    names = z.namelist()
assert "totonou-kakiokoshi/SKILL.md" in names and all(n.isascii() for n in names)
print(f"public/ を作りました: v{VERSION}（{UPDATED}） zip={ZIP} files={len(names)} "
      f"size={os.path.getsize(os.path.join(PUB, ZIP)) // 1024}KB")
