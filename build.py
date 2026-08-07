#!/usr/bin/env python3
"""monosashi.work を組む。

Artifact として作った職種ごとの1枚を本文に使い、共通の外枠（head・ナビ・フッター）を
かぶせて静的サイトにする。**本文は書き直さない。**同じものが2箇所にあると必ず片方が腐る
（zeimu-bench で、関税率表の平文を JSON と別に手で作って放置し、318税番が
区別できないファイルを配ったのと同じ失敗）。

    site/<職種>/body.html   Artifact の中身（<title> と <style> と本体）
    → dist/<職種>/index.html

使い方:
    python3 build.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
SITE = ROOT / "site"
DIST = ROOT / "dist"

PAGES = [
    ("kanzei", "通関 HS分類", "貨物の説明から輸入統計品目番号を決める", "2026-08"),
    ("zeimu", "税務 根拠条文", "税務の照会に対して国税庁が根拠とした条文を当てる", "2026-08"),
]

NAV = """<nav class="site-nav">
  <a class="brand" href="/">物差し</a>
  <span class="navlinks">
    <a href="/kanzei/">通関</a><a href="/zeimu/">税務</a><a href="/method/">測り方</a>
  </span>
</nav>"""

NAVCSS = """
  .site-nav{position:sticky;top:0;z-index:9;background:var(--ground);
    border-bottom:1px solid var(--rule);display:flex;justify-content:space-between;
    align-items:baseline;gap:1rem;padding:.7rem 1.5rem;
    font-family:var(--mono);font-size:.78rem;}
  .site-nav a{color:var(--ink);text-decoration:none;}
  .site-nav .brand{font-family:var(--mincho);font-size:1rem;font-weight:600;letter-spacing:.08em;}
  .site-nav .navlinks a{margin-left:1.1rem;color:var(--ink-soft);}
  .site-nav a:hover,.site-nav a:focus-visible{color:var(--verdigris);text-decoration:underline;}
  .site-nav a:focus-visible{outline:2px solid var(--verdigris);outline-offset:3px;}
  .wrap{padding-top:2.5rem;}
"""


def wrap(body_html, title, desc):
    """Artifact の本文に、共通の head とナビを付ける。"""
    style = re.search(r"<style>(.*?)</style>", body_html, re.S)
    css = (style.group(1) if style else "") + NAVCSS
    inner = re.sub(r"<title>.*?</title>\s*", "", body_html, flags=re.S)
    inner = re.sub(r"<style>.*?</style>\s*", "", inner, flags=re.S)
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}｜物差し</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}｜物差し">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<style>*{{box-sizing:border-box}}body{{margin:0}}{css}</style>
</head>
<body>
{NAV}
{inner}
</body>
</html>"""


def main():
    DIST.mkdir(exist_ok=True)
    for slug, title, desc, _ in PAGES:
        src = SITE / slug / "body.html"
        if not src.exists():
            print(f"  ! {slug}/body.html が無い")
            continue
        out = DIST / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            wrap(src.read_text(encoding="utf-8"), title, desc), encoding="utf-8")
        print(f"  /{slug}/  {(out/'index.html').stat().st_size/1e3:.0f} KB")

    for name in ("index", "method"):
        src = SITE / (f"{name}.html" if name == "index" else f"{name}/body.html")
        if not src.exists():
            continue
        out = DIST if name == "index" else DIST / name
        out.mkdir(parents=True, exist_ok=True)
        t = "AIは専門職の仕事をどこまでやれるか" if name == "index" else "測り方"
        d = ("職種ごとに、同じ物差しで実測して公開する。"
             if name == "index" else "4腕・較正・敵対テスト・追試の作法")
        (out / "index.html").write_text(
            wrap(src.read_text(encoding="utf-8"), t, d), encoding="utf-8")
        print(f"  /{'' if name=='index' else name+'/'}  "
              f"{(out/'index.html').stat().st_size/1e3:.0f} KB")

    tot = sum(p.stat().st_size for p in DIST.rglob("*.html"))
    print(f"→ {DIST}  {len(list(DIST.rglob('*.html')))} ページ / {tot/1e3:.0f} KB")


if __name__ == "__main__":
    main()
