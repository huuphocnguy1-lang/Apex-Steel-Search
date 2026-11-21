"""Knowledge library: built-in expert notes + 'Learn from web'.

Everything ends up as files in  <data dir>/knowledge/ :
    builtin/   expert notes shipped with the app (ESP, caster, HRM, PS, IDH, FM, cooling, coilers, hydraulics…)
    web/<topic>/   pages and PDFs collected from the internet (each with its source URL)
    ai_notes/<topic>/   notes written by the online AI model (only if you ask; marked 'verify')
    my_notes/  put your own files here (plant manuals, procedures…) – they count as plant documents
The folder is indexed like any watched folder, then digested (smart index + summaries) by the night analysis.
Answers then come from the library, offline, with sources.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from .config import data_dir

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 ApexSteelAnalyser")

# ------------------------------------------------------------------ topic packs
# key: (label, keywords that a page must contain, search queries)
PACKS = {
    "ESP": ("ESP – endless strip production",
            ["endless", "esp", "thin slab", "arvedi", "strip"],
            ["Arvedi ESP endless strip production process", "endless strip production thin slab direct rolling",
             "ESP line high reduction mill induction heater finishing mill", "endless rolling mass flow caster mill coupling",
             "thin slab casting and direct rolling technology"]),
    "Caster": ("Casting – thin slab caster",
               ["mould", "mold", "casting", "slab", "strand"],
               ["thin slab caster funnel mould oscillation", "continuous casting breakout prediction sticker",
                "SEN clogging mould level fluctuation causes", "continuous casting slab defects causes remedies",
                "soft reduction liquid core reduction thin slab"]),
    "HRM": ("Roughing / High Reduction Mill (RM, HRM)",
            ["roughing", "reduction", "stand", "roll", "mill"],
            ["high reduction mill thin slab roughing", "roughing mill camber wedge control",
             "hot rolling mill gaugemeter AGC mill modulus", "roll gap calibration hot strip mill procedure"]),
    "PS": ("Pendulum shear (PS) & piler",
           ["shear", "pendulum", "cut", "knife"],
           ["pendulum shear hot rolling transfer bar", "pendulum shear ESP plate mode piler",
            "crop shear knife clearance hot strip mill", "flying shear cut length control"]),
    "IDH": ("Induction heater, edge heater, descaler",
            ["induction", "heater", "descal", "scale", "temperature"],
            ["induction heating transfer bar hot strip mill", "edge heater transfer bar edge temperature",
             "hydraulic descaling hot strip mill nozzle pressure", "rolled in scale defect causes hot strip"]),
    "FM": ("Finishing mill (FM / HSM)",
           ["finishing", "looper", "tension", "gauge", "flatness", "stand"],
           ["hot strip finishing mill looper control tension", "hot strip mill AGC thickness control",
            "work roll bending shifting profile flatness control", "multi zone work roll cooling flatness",
            "hot strip mill cobble causes threading"]),
    "LC": ("Laminar cooling & coiling temperature",
           ["cooling", "coiling", "laminar", "temperature"],
           ["laminar cooling coiling temperature control model", "run out table cooling headers strip temperature",
            "coiling temperature deviation causes hot strip"]),
    "DC": ("High-speed shear & down coilers",
           ["coiler", "mandrel", "wrapper", "coil", "shear"],
           ["down coiler wrapper roll step control", "hot strip down coiler telescoping coil causes",
            "high speed flying shear endless rolling coil change", "mandrel expansion coiler pinch roll"]),
    "HYD": ("Hydraulics – fundamentals",
            ["hydraulic", "valve", "pump", "cylinder", "pressure"],
            ["industrial hydraulics fundamentals pumps valves cylinders", "ISO 1219 hydraulic symbols explained",
             "hydraulic accumulator precharge sizing", "proportional valve vs servo valve"]),
    "HYD-SERVO": ("Hydraulics – servo, HGC, loopers",
                  ["servo", "hydraulic", "gap", "valve", "cylinder"],
                  ["hydraulic gap control cylinder rolling mill servo valve", "servo valve null shift drift troubleshooting",
                   "hydraulic looper hot strip mill control", "servo hydraulic position control hunting oscillation"]),
    "HYD-TROUBLE": ("Hydraulics – troubleshooting & oil care",
                    ["hydraulic", "oil", "pressure", "filter", "contamination"],
                    ["hydraulic system troubleshooting guide pressure loss", "hydraulic oil contamination ISO 4406 servo valve",
                     "hydraulic pump cavitation causes", "hydraulic system overheating causes", "hydraulic flushing procedure"]),
}

BLOCK = ("youtube.", "youtu.be", "facebook.", "pinterest.", "instagram.", "twitter.", "x.com", "tiktok.", "amazon.",
         "alibaba.", "aliexpress.", "made-in-china.", "ebay.", "linkedin.com/jobs", "indeed.", "quora.com/profile",
         "reddit.com/user", "bilibili.", "douyin.", "taobao.", "jd.com", "1688.com")

MIN_CHARS = 1500


def root() -> str:
    p = os.path.join(str(data_dir()), "knowledge")
    for sub in ("builtin", "web", "ai_notes", "my_notes"):
        os.makedirs(os.path.join(p, sub), exist_ok=True)
    return p


def origin(path: str | None) -> str:
    """plant | builtin | web | ai — where a document comes from (used for source priority)."""
    if not path:
        return "plant"
    p = os.path.normcase(os.path.abspath(path))
    k = os.path.normcase(os.path.abspath(os.path.join(str(data_dir()), "knowledge")))
    if not p.startswith(k + os.sep):
        return "plant"
    rel = p[len(k) + 1:]
    first = rel.split(os.sep, 1)[0]
    return {"builtin": "builtin", "web": "web", "ai_notes": "ai"}.get(first, "plant")


ORIGIN_LABEL = {"plant": "PLANT DOCUMENT", "builtin": "BUILT-IN EXPERT NOTE", "web": "WEB SOURCE",
                "ai": "AI NOTE (unverified)"}
ORIGIN_ICON = {"plant": "🏭 ", "builtin": "📘 ", "web": "🌐 ", "ai": "🤖 "}
ORIGIN_BONUS = {"plant": 0.03, "builtin": 0.0, "web": -0.02, "ai": -0.04}


def install_builtin() -> int:
    """Copy the expert notes shipped with the app into the knowledge folder (only new / changed ones)."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb")
    dst = os.path.join(root(), "builtin")
    n = 0
    if not os.path.isdir(src):
        return 0
    for f in os.listdir(src):
        if not f.endswith(".md"):
            continue
        a, b = os.path.join(src, f), os.path.join(dst, f)
        try:
            if not os.path.exists(b) or open(a, "rb").read() != open(b, "rb").read():
                shutil.copyfile(a, b)
                n += 1
        except OSError:
            pass
    return n


def builtin_files() -> list[str]:
    d = os.path.join(root(), "builtin")
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".md"))


# ------------------------------------------------------------------ manifest of learned sources
def _manifest_path():
    return os.path.join(root(), "manifest.json")


def load_manifest() -> dict:
    try:
        with open(_manifest_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_manifest(m: dict):
    tmp = _manifest_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _manifest_path())


def remove_source(key: str):
    m = load_manifest()
    e = m.pop(key, None)
    if e and e.get("file") and os.path.exists(e["file"]):
        try:
            os.remove(e["file"])
        except OSError:
            pass
    save_manifest(m)


def counts_by_topic() -> dict:
    out = {}
    for e in load_manifest().values():
        out[e.get("topic", "?")] = out.get(e.get("topic", "?"), 0) + 1
    return out


# ------------------------------------------------------------------ http
def _open(url: str, data: bytes | None = None, timeout: int = 20):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"})
    return urllib.request.urlopen(req, timeout=timeout)


def _get(url: str, limit: int = 15_000_000, timeout: int = 20) -> tuple[bytes, str]:
    with _open(url, timeout=timeout) as r:
        ctype = (r.headers.get("Content-Type") or "").lower()
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError("file too large")
    return data, ctype


# ------------------------------------------------------------------ search engines
def _clean_link(u: str) -> str | None:
    u = html.unescape(u)
    if u.startswith("//"):
        u = "https:" + u
    if "bing.com/ck/a" in u:            # Bing redirect: real URL is base64 in the 'u' parameter ("a1" + base64url)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
        enc = (q.get("u", [""])[0] or "")
        if enc.startswith("a1"):
            import base64
            try:
                b = enc[2:]
                u = base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode("utf-8", "ignore")
            except Exception:
                return None
    if "duckduckgo.com/l/?" in u:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
        u = q.get("uddg", [None])[0]
    if not u or not u.startswith("http"):
        return None
    if any(b in u.lower() for b in BLOCK):
        return None
    if re.search(r"bing\.com|duckduckgo\.com|microsoft\.com/.*bing|go\.microsoft", u):
        return None
    return u


def search_bing(query: str, n: int = 6, cn: bool = False) -> list[str]:
    host = "cn.bing.com" if cn else "www.bing.com"
    data, _ = _get(f"https://{host}/search?q={urllib.parse.quote(query)}&setlang=en&count=15", timeout=15)
    page = data.decode("utf-8", "ignore")
    links = re.findall(r'<li class="b_algo".*?<h2[^>]*>\s*<a[^>]+href="([^"]+)"', page, flags=re.S)
    out = []
    for u in links:
        u = _clean_link(u)
        if u and u not in out:
            out.append(u)
    return out[:n]


def search_ddg(query: str, n: int = 6) -> list[str]:
    data, _ = _get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query), timeout=15)
    page = data.decode("utf-8", "ignore")
    out = []
    for u in re.findall(r'class="result__a"[^>]+href="([^"]+)"', page):
        u = _clean_link(u)
        if u and u not in out:
            out.append(u)
    return out[:n]


def search_wikipedia(query: str, n: int = 2) -> list[str]:
    data, _ = _get("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=%d&srsearch=%s"
                   % (n, urllib.parse.quote(query)), timeout=15)
    hits = json.loads(data.decode("utf-8")).get("query", {}).get("search", [])
    return ["https://en.wikipedia.org/wiki/" + urllib.parse.quote(h["title"].replace(" ", "_")) for h in hits]


def web_search(query: str, n: int = 4, engine: str = "auto", log=None) -> list[str]:
    """Search the web. 'auto' tries Bing, then Bing China (works in mainland China), then DuckDuckGo."""
    order = {"auto": ["bing", "bing_cn", "ddg"], "bing": ["bing"], "bing_cn": ["bing_cn"], "ddg": ["ddg"]}.get(engine, ["bing"])
    last = None
    for e in order:
        try:
            res = (search_bing(query, n + 4) if e == "bing" else search_bing(query, n + 4, cn=True) if e == "bing_cn"
                   else search_ddg(query, n + 4))
            if res:
                return res
        except Exception as ex:
            last = ex
            if log:
                log(f"   search engine {e} not reachable ({type(ex).__name__})")
    if last and log:
        log("   no search engine reachable — check the internet connection / proxy")
    return []


# ------------------------------------------------------------------ html → text
class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "button", "select"}
    BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "tr", "pre", "blockquote", "dd", "dt", "figcaption", "br", "div",
              "section", "article", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.title, self._in_title = [], 0, "", False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in ("h1", "h2", "h3", "h4"):
            self.out.append("\n\n## " if tag != "h1" else "\n\n# ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag in self.BLOCKS:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self.BLOCKS:
            self.out.append("\n")

    def handle_data(self, d):
        if self._in_title:
            self.title += d
        elif not self.skip:
            self.out.append(d)


def html_to_text(page: str) -> tuple[str, str]:
    p = _Text()
    try:
        p.feed(page)
    except Exception:
        pass
    txt = "".join(p.out)
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    lines = [l.strip() for l in txt.split("\n")]
    keep = []
    for l in lines:
        if not l:
            if keep and keep[-1] != "":
                keep.append("")
            continue
        # drop menu-like short lines (cookie banners, links) unless headings / list items with content
        if len(l) < 25 and not l.startswith("#") and not re.search(r"\d", l):
            continue
        keep.append(l)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip(), html.unescape(p.title.strip())


def _slug(s: str, n: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return (s or "page")[:n]


def relevant(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return sum(1 for k in keywords if k.lower() in t) >= min(2, len(keywords))


# ------------------------------------------------------------------ fetch & save one source
def fetch_and_save(url: str, topic: str, keywords: list[str], manifest: dict, log=None) -> str | None:
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    if key in manifest:
        return None
    data, ctype = _get(url)
    folder = os.path.join(root(), "web", _slug(topic, 30))
    os.makedirs(folder, exist_ok=True)
    date = time.strftime("%Y-%m-%d")
    if "pdf" in ctype or url.lower().split("?")[0].endswith(".pdf"):
        if not data.startswith(b"%PDF"):
            return None
        name = _slug(os.path.basename(urllib.parse.urlparse(url).path).rsplit(".", 1)[0] or "document") + f"_{key[:6]}.pdf"
        path = os.path.join(folder, name)
        with open(path, "wb") as f:
            f.write(data)
        with open(path + ".source", "w", encoding="utf-8") as f:
            f.write(f"Source: {url}\nTopic: {topic}\nDownloaded: {date}\n")
        title = name
    else:
        enc = "utf-8"
        m = re.search(r"charset=([\w-]+)", ctype)
        if m:
            enc = m.group(1)
        page = data.decode(enc, "ignore")
        text, title = html_to_text(page)
        if len(text) < MIN_CHARS or not relevant(text, keywords):
            if log:
                log(f"   skipped (too short or off-topic): {url[:90]}")
            return None
        title = (title or url)[:150]
        path = os.path.join(folder, _slug(title) + f"_{key[:6]}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\nSource: {url}\nTopic: {topic}\nDownloaded: {date}\n"
                    f"(Web source collected by Apex Steel Analyser — check against plant documents.)\n\n{text[:120_000]}\n")
    manifest[key] = {"url": url, "title": title, "topic": topic, "file": path, "date": date}
    return path


# ------------------------------------------------------------------ main job
def learn(topics: list[str], custom: list[str] | None = None, urls: list[str] | None = None, per_query: int = 2,
          engine: str = "auto", wikipedia: bool = True, ai=None, ai_notes: bool = False,
          log=None, progress=None, should_stop=None) -> int:
    log = log or (lambda m: None)
    progress = progress or (lambda i, n, m: None)
    should_stop = should_stop or (lambda: False)
    manifest = load_manifest()
    jobs = []  # (topic, keywords, query)
    for t in topics:
        if t in PACKS:
            label, kw, qs = PACKS[t]
            jobs += [(t, kw, q) for q in qs]
    for q in custom or []:
        q = q.strip()
        if q:
            words = [w for w in re.findall(r"[A-Za-z]{4,}", q)][:5] or [q]
            jobs.append(("Custom", words, q))
    saved, total = 0, len(jobs) + len(urls or [])
    step = 0
    for u in urls or []:
        if should_stop():
            break
        step += 1
        progress(step, total, "downloading your links")
        try:
            p = fetch_and_save(u.strip(), "My links", ["the"], manifest, log)
            if p:
                saved += 1
                log(f"✔ saved: {os.path.basename(p)}")
        except Exception as e:
            log(f"✘ {u[:80]}: {e}")
    for topic, kw, q in jobs:
        if should_stop():
            log("Learning stopped.")
            break
        step += 1
        progress(step, total, f"learning: {topic}")
        log(f"🔎 {topic}: {q}")
        links = web_search(q, per_query + 3, engine, log)
        if wikipedia and topic != "Custom":
            try:
                links = search_wikipedia(q, 1) + links
            except Exception:
                pass
        got = 0
        for u in links:
            if got >= per_query or should_stop():
                break
            try:
                p = fetch_and_save(u, topic, kw, manifest, log)
            except Exception as e:
                log(f"   ✘ {u[:80]} ({type(e).__name__})")
                continue
            if p:
                got += 1
                saved += 1
                log(f"   ✔ {os.path.basename(p)}")
        save_manifest(manifest)
    if ai_notes and ai is not None:
        saved += write_ai_notes(ai, topics, custom, log, should_stop)
    save_manifest(manifest)
    log(f"📚 Learning finished: {saved} new source(s). They are now being indexed and digested.")
    return saved


def write_ai_notes(ai, topics, custom, log, should_stop) -> int:
    """Ask the (online) AI model for a structured engineering note per topic. Marked as unverified."""
    n = 0
    items = [(t, PACKS[t][0]) for t in topics if t in PACKS] + [("Custom", c) for c in (custom or []) if c.strip()]
    for key, label in items:
        if should_stop():
            break
        log(f"🤖 writing AI note: {label}")
        msgs = [{"role": "system", "content": "You are a senior steel-plant process and hydraulics engineer. Write precise, "
                 "practical engineering notes for commissioning and maintenance engineers. Use headings, tables, typical "
                 "values with units (say 'typical' — plant values may differ), troubleshooting tables "
                 "(symptom → causes → checks) and safety points. English. No marketing."},
                {"role": "user", "content": f"Write a detailed technical note (900–1300 words) on: {label} "
                 "in the context of an ESP endless strip production line / hot strip mill."}]
        try:
            txt = ai.chat(msgs, deep=False)
        except Exception as e:
            log(f"   ✘ AI note failed: {e}")
            break
        folder = os.path.join(root(), "ai_notes", _slug(key, 30))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, _slug(label) + ".md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# AI note: {label}\n\n(Generated by {ai.chat_model_label()} on {time.strftime('%Y-%m-%d')} — "
                    f"unverified, check against plant documents.)\n\n{txt}\n")
        n += 1
    return n
