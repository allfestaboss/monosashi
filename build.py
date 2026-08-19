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
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
SITE = ROOT / "site"
DIST = ROOT / "dist"

# ベンチの正本。**撤回文はここからしか読まない。**サイト側に書き写さない。
# 書き写すと同じ文が2箇所に存在し、片方が腐る（zeimu の関税率表と同じ失敗）。
BENCH = ROOT.parent / "big-business"

# `<p>` の本文が `Version X.Y.Z` で始まる段落＝その版の変更記録。
# 9リポの .zenodo.json で較正済み（誤検出ゼロ・取りこぼしゼロ）。
# 本文中の言及（"repairing the v1.1.0 defect"）は**数えない**。
_BLOCK = re.compile(r"<p>.*?</p>", re.S)
_HEAD = re.compile(r"^\s*Version\s+(\d+\.\d+\.\d+)")


def _key(v):
    return [int(x) for x in v.split(".")]


def bench_state(name):
    """ベンチの現行版・DOI・版段落を読む。読めなければ None。

    多くは big-business/ の下にあるが、そこに無いものもある
    （shoken-model は 01_projects 直下で、公開用の複製は -public 付き）。
    見つかった最初の場所を使う。
    """
    # 公開用の複製(-public)を作業リポジトリより先に見る。
    # 発行済みDOIは公開側にしか書き戻らないので、順序を逆にすると DOI が None になる（踏んだ）。
    for cand in (BENCH / name, ROOT.parent / f"{name}-public", ROOT.parent / name):
        if (cand / "CITATION.cff").exists() and (cand / ".zenodo.json").exists():
            repo = cand
            break
    else:
        return None
    cff = repo / "CITATION.cff"
    zj = repo / ".zenodo.json"
    t = cff.read_text(encoding="utf-8")
    ver = re.search(r'^version:\s*"?([^"\s]+)"?', t, re.M)
    doi = re.search(r'^doi:\s*"?([^"\s]+)"?', t, re.M)
    desc = json.loads(zj.read_text(encoding="utf-8")).get("description", "")
    paras = {}
    for m in _BLOCK.finditer(desc):
        text = re.sub("<[^>]+>", "", m.group(0))
        h = _HEAD.match(text)
        if h:
            paras[h.group(1)] = m.group(0)
    return {
        "version": ver.group(1) if ver else None,
        "doi": doi.group(1) if doi else None,
        "paragraphs": paras,
    }


def version_notice(slug, site_dir=None, bench_name=None):
    """版の対応を出す。(HTML, 関門を落とすか) を返す。

    site_dir を渡すとサブドメイン用の置き場を見る（既定は site/<slug>/）。

    **reviewed.json は2欄を別々に持つ。1欄で兼ねてはいけない。**

      version      本文がどの版に対応するか。**事実**。読者に見せる（版差ブロックの根拠）
      acknowledged 人がどの版まで読んで判断したか。**判断**。関門の根拠

    兼ねると「版差ブロックを出したままデプロイする」ができなくなる。
    ブロックが出る条件（本文が古い）と関門が落ちる条件（誰も読んでいない）は
    別物で、**本文を据え置くと決めたなら前者は残り後者は解消する**のが正しい。

    一致  → 1行。 不一致 → 間の版の段落を **そのまま** 並べる。要約しない。
    要約した瞬間に二重管理が復活する。読みにくくても原文のほうが正しい。
    枠の日本語は全て変数の差し込みで、こちらが書いた文は1つも無い。
    """
    mark_path = (site_dir or SITE / slug) / "reviewed.json"
    if not mark_path.exists():
        return "", False
    mark = json.loads(mark_path.read_text(encoding="utf-8"))
    st = bench_state(bench_name or mark["bench"])
    if st is None or not st["version"]:
        return "", False

    seen, cur, doi = mark["version"], st["version"], st["doi"]
    ack = mark.get("acknowledged", seen)   # 無ければ本文の版と同じ＝未確認扱い
    unread = _key(ack) < _key(cur)
    if seen == cur:
        return (f'<div class="vernote">この記事は <code>{mark["bench"]}</code> '
                f'<strong>v{cur}</strong> に対応します（DOI {doi}）。</div>'), False

    newer = sorted((v for v in st["paragraphs"] if _key(v) > _key(seen)), key=_key)
    blocks = "".join(st["paragraphs"][v] for v in newer)
    note = ("" if unread else
            f'<div class="vd-n">{mark.get("note", "")}'
            f'<span class="dim">（確認 {mark.get("ack_date", mark["date"])}）</span></div>')
    return (f'<div class="verdiff">'
            f'<div class="vd-h"><code>{mark["bench"]}</code> は '
            f'<strong>v{cur}</strong> に更新されています。'
            f'この記事は <strong>v{seen}</strong>（{mark["date"]}）に対応します。</div>'
            f'<div class="vd-b">以下は Zenodo に登録された変更記録の原文です'
            f'（DOI {doi}）。</div>{blocks}{note}</div>'), unread

PAGES = [
    ("cad", "建築2D図面 DXF", "間取りを完全に与えて作図能力だけを測る", "2026-08"),
    ("kanzei", "通関 HS分類", "貨物の説明から輸入統計品目番号を決める", "2026-08"),
    ("zeimu", "税務 根拠条文", "税務の照会に対して国税庁が根拠とした条文を当てる", "2026-08"),
]

NAV = """<nav class="site-nav">
  <a class="brand" href="/">物差し</a>
  <span class="navlinks">
    <a href="/cad/">建築CAD</a><a href="/kanzei/">通関</a><a href="/zeimu/">税務</a><a href="/method/">測り方</a><a href="/changes/">変更と撤回</a>
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
  .vernote{max-width:47rem;margin:1.6rem auto -1rem;padding:0 1.5rem;
    font-family:var(--mono);font-size:.74rem;color:var(--ink-soft);}
  .verdiff{max-width:47rem;margin:1.6rem auto -.5rem;padding:1rem 1.2rem;
    border:2px solid var(--oxide);background:var(--ground2);
    display:flex;flex-direction:column;gap:.7rem;}
  .verdiff .vd-h{font-family:var(--mincho);font-size:1.02rem;font-weight:600;line-height:1.6;}
  .verdiff .vd-b{font-family:var(--mono);font-size:.72rem;color:var(--ink-soft);}
  .verdiff .vd-n{border-top:1px solid var(--rule);padding-top:.6rem;
    font-size:.8rem;line-height:1.7;color:var(--ink-soft);}
  .verdiff .dim{opacity:.75;}
  .verdiff p{font-size:.84rem;line-height:1.75;color:var(--ink-soft);margin:0;}
  .verdiff p strong{color:var(--ink);}
  .verdiff code{font-family:var(--mono);font-size:.85em;
    background:var(--chip);padding:.1em .35em;border-radius:2px;}
"""


def wrap(body_html, title, desc, notice=""):
    """Artifact の本文に、共通の head とナビを付ける。**本文は書き直さない。**"""
    style = re.search(r"<style>(.*?)</style>", body_html, re.S)
    css = (style.group(1) if style else "") + NAVCSS
    inner = re.sub(r"<title>.*?</title>\s*", "", body_html, flags=re.S)
    inner = re.sub(r"<style>.*?</style>\s*", "", inner, flags=re.S)
    inner = notice + inner
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


# --- サブドメイン ---------------------------------------------------------
# 職種はパスで切る（同じ物差しで測ったものだから）。
# 商圏モデルは**同じ物差しで測っていない**——被験者がAIではなく日本の店舗立地なので、
# パスに混ぜると「同じ物差し」が壊れる。だからサブドメインに出して、
# 同じ家の別棟であることを構造で示す。
SUBSITES = [
    {
        "slug": "shoken",
        "src": ROOT / "site-shoken" / "body.html",
        "dist": ROOT / "dist-shoken",
        "bench": "shoken-model",
        "title": "どこかは当たる、何かは当たらない",
        "desc": "全国471,024メッシュ・30業種で測った店舗立地の予測可能性。",
        "repo": "https://github.com/allfestaboss/shoken-model",
    },
]

SUBNAV = """<nav class="site-nav">
  <a class="brand" href="https://monosashi.work/">物差し</a>
  <span class="navlinks">
    <a href="{repo}">コードとデータ</a><a href="https://monosashi.work/">AI実務到達度インデックス</a>
  </span>
</nav>"""


def build_subsites():
    """サブドメインのページを作る。版ドリフトの仕組みは職種と同じものを使う。"""
    global NAV
    stale = []
    for cfg in SUBSITES:
        if not cfg["src"].exists():
            print(f"  ! {cfg['slug']}: body.html が無い")
            continue
        notice, behind = version_notice(cfg["slug"], site_dir=ROOT / f"site-{cfg['slug']}",
                                        bench_name=cfg["bench"])
        if behind:
            stale.append(cfg["slug"])
        cfg["dist"].mkdir(parents=True, exist_ok=True)
        keep, NAV = NAV, SUBNAV.format(repo=cfg["repo"])
        try:
            html = wrap(cfg["src"].read_text(encoding="utf-8"),
                        cfg["title"], cfg["desc"], notice)
        finally:
            NAV = keep
        (cfg["dist"] / "index.html").write_text(html, encoding="utf-8")
        print(f"  {cfg['slug']}.monosashi.work  "
              f"{(cfg['dist']/'index.html').stat().st_size/1e3:.0f} KB"
              f"{'  ← 版が進んでいる' if behind else ''}")
    return stale


def main():
    DIST.mkdir(exist_ok=True)
    stale = []
    for slug, title, desc, _ in PAGES:
        src = SITE / slug / "body.html"
        if not src.exists():
            print(f"  ! {slug}/body.html が無い")
            continue
        notice, behind = version_notice(slug)
        if behind:
            stale.append(slug)
        out = DIST / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            wrap(src.read_text(encoding="utf-8"), title, desc, notice), encoding="utf-8")
        print(f"  /{slug}/  {(out/'index.html').stat().st_size/1e3:.0f} KB"
              f"{'  ← 版が進んでいる' if behind else ''}")

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

    build_changes()
    stale += build_subsites()

    tot = sum(p.stat().st_size for p in DIST.rglob("*.html"))
    print(f"→ {DIST}  {len(list(DIST.rglob('*.html')))} ページ / {tot/1e3:.0f} KB")

    if stale:
        print()
        print(f"[NG] 版が進んだのに確認印が古い: {', '.join(stale)}")
        print("     ページは生成してある。**差し込まれた内容を見てから**")
        print("     site/<slug>/reviewed.json の version と date を進めること。")
        print("     （見る前に印を打つと、確認するために確認印を打つ順序の逆転になる）")
        return 1
    return 0


# 掲載していない本も載せる。掲載の有無は読者の都合で、撤回の有無とは関係がない。
LEDGER = [
    ("kanzei-bench", "通関 HS分類", "/kanzei/"),
    ("zeimu-bench", "税務 根拠条文", "/zeimu/"),
    ("cad-bench", "建築2D図面 DXF", "/cad/"),
    ("sekisan-bench", "積算", None),
    ("doboku-bench", "土木CAD SXF", None),
    ("jiban-bench", "地盤 液状化判定", None),
    ("kikai-bench", "機械 STEP AP242", None),
    ("bim-bench", "建築BIM IFC", None),
    ("ai-reach-paper", "方法論論文（プレプリント）", None),
]


def build_changes():
    """/changes/ — 全ベンチ横断の版と撤回の台帳。

    論文 §6.3 が「欠陥件数は公表すべきで、公表しないベンチマークは
    『見ていない』のか『言っていない』のか読者に区別がつかない」と主張している。
    その公開面がこれ。**文面は1つも書かない。**全て .zenodo.json から読む。
    """
    rows, blocks = [], []
    for name, label, href in LEDGER:
        st = bench_state(name)
        if st is None:
            continue
        vers = sorted(st["paragraphs"], key=_key)
        link = f'<a href="{href}">{label}</a>' if href else f'{label}<span class="dim">（未掲載）</span>'
        rows.append(
            f'<tr><td>{link}</td><td class="num">v{st["version"]}</td>'
            f'<td class="num">{len(vers)}</td>'
            f'<td class="num dim">{st["doi"] or "—"}</td></tr>')
        if vers:
            blocks.append(
                f'<section><h2>{label} <span class="dim">{name}</span></h2>'
                + "".join(st["paragraphs"][v] for v in reversed(vers))
                + "</section>")

    body = f"""<title>変更と撤回</title>
<div class="wrap">
<header>
  <div class="eyebrow">Changes &amp; retractions</div>
  <h1>変更と撤回</h1>
  <p class="sub">出した結果を後から取り下げたときの記録を、まとめてここに置く。
  サイトに載せていない業種も含める。<strong>載せているかどうかは読者の都合であって、
  撤回があったかどうかとは関係がない。</strong></p>
</header>
<section>
  <h2>いまの版</h2>
  <div class="scroll"><table>
  <tr><th>業種</th><th>現行版</th><th>版の記録</th><th>DOI（この版）</th></tr>
  {''.join(rows)}
  </table></div>
  <p class="dim">この表もこの下の原文も、各リポジトリの <code>.zenodo.json</code> と
  <code>CITATION.cff</code> から生成している。<strong>このページに手で書いた文は無い。</strong>
  撤回の記録を2箇所に持つと、片方が腐るため。</p>
</section>
{''.join(blocks)}
<footer>
  原文は Zenodo に登録された英文をそのまま出している。訳すと、それが2箇所目の撤回文になる。
</footer>
</div>"""
    out = DIST / "changes"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        wrap(body, "変更と撤回", "出した結果を後から取り下げたときの記録"),
        encoding="utf-8")
    print(f"  /changes/  {(out/'index.html').stat().st_size/1e3:.0f} KB")


def check():
    """書かずに版のドリフトだけ見る。日次ダイジェストから毎晩呼ぶ用。

    **build の関門だけでは、実際に起きた壊れ方を捕まえられない。**
    2026-08-10〜12 に5リポが新版を出したがサイトは誰も触らず、build を
    走らせていないので関門は一度も鳴らなかった。デプロイ時にしか見ない検査は、
    デプロイしない期間のドリフトに無力である。だから毎晩こちらから見に行く。
    """
    behind, ok = [], []
    for slug, *_ in PAGES:
        mark_path = SITE / slug / "reviewed.json"
        if not mark_path.exists():
            continue
        mark = json.loads(mark_path.read_text(encoding="utf-8"))
        st = bench_state(mark["bench"])
        if st is None or not st["version"]:
            continue
        ack = mark.get("acknowledged", mark["version"])
        if _key(ack) < _key(st["version"]):
            behind.append((slug, mark["bench"], ack, st["version"]))
        else:
            ok.append((slug, mark["bench"], st["version"]))
    for slug, bench, ack, cur in behind:
        print(f"  [!] /{slug}/  {bench} が v{cur} に進んでいる（確認済みは v{ack}）")
    if not behind:
        print(f"  版のドリフトなし（{len(ok)}ページ確認）")
    return 1 if behind else 0


if __name__ == "__main__":
    import sys
    raise SystemExit(check() if "--check" in sys.argv else main())
