"""Keyword search, smart (meaning) search and the AI assistant (answers with sources)."""
import difflib
import html
import re

from . import meta


class SmartUnavailable(Exception):
    pass


FILTER_KINDS = [
    ("All types", "all"), ("Drawings", "drawing"), ("PDF", "pdf"), ("Word", "word"), ("Excel", "excel"),
    ("Photos", "photo"), ("Email", "email"), ("Scans (OCR)", "scan"),
    ("Mechanical drawings", "t:mechanical"), ("Hydraulic schematics", "t:hydraulic"), ("P&ID (process)", "t:pid"),
    ("Electrical schematics", "t:electrical"),
]


def tokens(q: str) -> list[str]:
    out = []
    for t in re.split(r"[\s,;/]+", q.lower()):
        t = t.strip("\"'()[]{}!?:")
        if len(t) >= 2 or re.match(r"[一-鿿]", t or " "):
            if t and t not in out:
                out.append(t)
    return out


def _like(t: str) -> str:
    return "%" + t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _passes(r, filters: dict, latest_map: dict) -> bool:
    k = filters.get("kind", "all")
    ext, kind = r["ext"], r["kind"]
    if k == "drawing" and kind != "drawing":
        return False
    if k == "pdf" and ext != "pdf":
        return False
    if k == "word" and ext not in ("docx", "docm", "doc", "rtf", "odt"):
        return False
    if k == "excel" and ext not in ("xlsx", "xlsm", "xls", "csv"):
        return False
    if k == "photo" and kind != "photo":
        return False
    if k == "email" and kind != "email":
        return False
    if k == "scan" and not r["ocr"]:
        return False
    if k.startswith("t:") and (r["dtype"] if "dtype" in r.keys() else None) != k[2:]:
        return False
    p = filters.get("project")
    if p and p != "all" and r["project"] != p:
        return False
    if filters.get("latest") and r["dno"] and latest_map.get(r["dno"]) != r["rev"]:
        return False
    return True


def snippet(text: str, terms, n: int = 130) -> str:
    if not text:
        return ""
    low = text.lower()
    pos = -1
    for t in terms:
        i = low.find(t.lower())
        if i >= 0 and (pos < 0 or i < pos):
            pos = i
    if pos < 0:
        s = text[: n * 2]
        return s + ("…" if len(text) > n * 2 else "")
    a, b = max(0, pos - n), min(len(text), pos + n)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


def highlight_html(text: str, terms) -> str:
    s = html.escape(text)
    terms = sorted({t for t in terms if t and len(t) >= 1}, key=len, reverse=True)
    if not terms:
        return s
    pat = re.compile("(" + "|".join(re.escape(html.escape(t)) for t in terms) + ")", re.I)
    return pat.sub(r'<span style="background:#FFE48A">\1</span>', s)


def _result(r, score, label, terms, latest_map, extra=None):
    body = r["body"] if "body" in r.keys() else ""
    d = {k: r[k] for k in r.keys() if k != "body"}
    d.update(score=score, label=label, terms=list(terms), snippet=snippet(body or "", terms),
             latest=(latest_map.get(r["dno"]) == r["rev"]) if r["dno"] else None, reasons=[])
    if extra:
        d.update(extra)
    return d


def _sort(results, filters):
    if filters.get("sort") == "date":
        results.sort(key=lambda d: d.get("mtime") or 0, reverse=True)
    return results


# ------------------------------------------------------------------ keyword
def keyword_search(db, q: str, filters: dict | None = None, limit: int = 200) -> dict:
    filters = filters or {}
    toks = tokens(q)
    if not toks:
        return {"results": [], "note": ""}
    cand = set()
    long_t = [t for t in toks if len(t) >= 3] if db.trigram else []
    short_t = [t for t in toks if t not in long_t]
    if long_t:
        fq = " OR ".join('"' + t.replace('"', '""') + '"' for t in long_t)
        cand |= {r[0] for r in db.q("SELECT rowid FROM fts WHERE fts MATCH ? LIMIT 5000", (fq,))}
    for t in short_t:
        lk = _like(t)
        cand |= {r[0] for r in db.q("SELECT f.id FROM files f LEFT JOIN texts t ON t.file_id=f.id "
                                    "WHERE t.body LIKE ? ESCAPE '\\' OR f.name LIKE ? ESCAPE '\\' "
                                    "OR f.tags LIKE ? ESCAPE '\\' LIMIT 5000", (lk, lk, lk))}
    latest_map = db.latest_revs()
    scored = []
    for r in db.rows_with_body(cand):
        if not _passes(r, filters, latest_map):
            continue
        name = (r["name"] + " " + (r["title"] or "")).lower()
        hay = ((r["body"] or "") + " " + (r["tags"] or "")).lower()
        hits, sc = 0, 0
        for t in toks:
            a, b = name.count(t), hay.count(t)
            if a or b:
                hits += 1
            sc += a * 5 + min(b, 50)
        if hits:
            scored.append((hits * 1000 + sc, hits, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    res = [_result(r, s, f"{h}/{len(toks)} words", toks, latest_map) for s, h, r in scored[:limit]]
    return {"results": _sort(res, filters), "note": f"{len(scored)} result(s)"}


# ------------------------------------------------------------------ smart
def smart_search(db, ai, q: str, filters: dict | None = None, limit: int = 100) -> dict:
    import numpy as np
    filters = filters or {}
    if ai is None:
        raise SmartUnavailable("AI engine not configured")
    mat, chunk_ids, file_ids = db.vector_matrix(ai.embed_key())
    if mat is None:
        raise SmartUnavailable("The smart index is empty. Start the AI engine (Ollama) and click "
                               "'Build smart index' in Folders & index.")
    qv = np.asarray(ai.embed([q])[0], dtype=np.float32)
    qv /= (np.linalg.norm(qv) or 1.0)
    if qv.shape[0] != mat.shape[1]:
        raise SmartUnavailable("Smart index was built with another model — rebuild it.")
    sims = np.empty(mat.shape[0], dtype=np.float32)
    step = 20000
    for i in range(0, mat.shape[0], step):
        sims[i:i + step] = mat[i:i + step].astype(np.float32) @ qv
    order = np.argsort(-sims)[:1500]
    best = {}
    for idx in order:
        fid = file_ids[idx]
        if fid not in best:
            best[fid] = (float(sims[idx]), chunk_ids[idx])
    # fuse with keyword ranking (hybrid search)
    kw = keyword_search(db, q, {}, limit=300)["results"]
    kw_rank = {d["id"]: i for i, d in enumerate(kw)}
    vec_rank = {fid: i for i, fid in enumerate(best)}
    ids = set(best) | set(kw_rank)
    fused = sorted(ids, key=lambda f: -(1 / (60 + vec_rank.get(f, 10_000)) + 0.6 / (60 + kw_rank.get(f, 10_000))))
    latest_map = db.latest_revs()
    rows = {r["id"]: r for r in db.rows_with_body(fused[: limit * 3])}
    texts = db.chunk_texts([best[f][1] for f in fused[: limit * 3] if f in best])
    qlang = meta.language(q)
    qtok = tokens(q)
    res = []
    for f in fused:
        r = rows.get(f)
        if r is None or not _passes(r, filters, latest_map):
            continue
        sim = best.get(f, (0.0, None))[0]
        pct = int(round(max(0.0, min(1.0, (sim - 0.25) / 0.6)) * 100)) if f in best else 0
        if f in kw_rank:
            pct = max(pct, 55)
        d = _result(r, pct, f"{pct}% meaning", qtok, latest_map)
        ch = texts.get(best[f][1]) if f in best else None
        if ch:
            d["snippet"] = snippet(ch.split("\n", 1)[-1], qtok)
        if r["lang"] not in ("—", qlang):
            d["reasons"].append(f"cross-language ({r['lang']})")
        if f in best and f not in kw_rank:
            d["reasons"].append("found by meaning")
        res.append(d)
        if len(res) >= limit:
            break
    return {"results": _sort(res, filters), "note": f"{len(res)} result(s) ranked by meaning"}


# ------------------------------------------------------------------ assistant
SOURCE_RULES = (
    "Sources are labelled: PLANT DOCUMENT (the user's own files — highest priority), PAST CASE (plant lessons "
    "learned), BUILT-IN EXPERT NOTE (general expert knowledge), WEB SOURCE (internet, check), AI NOTE (unverified). "
    "If sources disagree, follow the PLANT DOCUMENT and say that general sources differ. ")
SYSTEM_PROMPT = (
    "You are Apex AI, an engineering assistant specialised in ESP endless strip production lines (thin slab caster, "
    "high reduction mill, pendulum shear, induction heater, finishing mill, laminar cooling, high-speed shear, down "
    "coilers), industrial hydraulics and the steel process, for installation, commissioning and maintenance engineers. "
    + SOURCE_RULES +
    "Answer from the numbered sources given. Cite sources like [1] or [2][3] after each fact. "
    "Give figures exactly (bolt grades, torques, tolerances, dimensions, dates). "
    "If the sources do not contain the answer, say so clearly. "
    "Answer in the same language as the question. Use short bullet points when useful."
)


def _gather_sources(db, ai, question: str, max_sources: int = 5, budget: int = 6000):
    """Finds the most relevant passages. Short texts = faster answers. Pre-summaries (night analysis) are used
    first when they exist: they condense a whole document in a few lines."""
    picks = []  # (file_id, text)
    try:
        import numpy as np
        mat, chunk_ids, file_ids = db.vector_matrix(ai.embed_key())
        if mat is None:
            raise SmartUnavailable("")
        qv = np.asarray(ai.embed([question])[0], dtype=np.float32)
        qv /= (np.linalg.norm(qv) or 1.0)
        sims = mat.astype(np.float32) @ qv
        order = list(np.argsort(-sims)[:48])
        try:   # source priority: plant documents first, then built-in notes, web, AI notes
            from .knowledge import ORIGIN_BONUS, origin
            paths = {}
            for i in order:
                fid = file_ids[i]
                if fid not in paths:
                    r = db.get(fid)
                    paths[fid] = r["path"] if r is not None else None
            order.sort(key=lambda i: -(float(sims[i]) + ORIGIN_BONUS.get(origin(paths[file_ids[i]]), 0.0)))
        except Exception:
            pass
        order = order[:24]
        texts = db.chunk_texts([chunk_ids[i] for i in order])
        for i in order:
            picks.append((file_ids[i], texts.get(chunk_ids[i], "")))
    except Exception:
        for d in keyword_search(db, question, {}, limit=8)["results"]:
            body = db.body(d["id"])
            picks.append((d["id"], snippet(body, d["terms"], n=700)))
    by_file, used = {}, 0
    for fid, t in picks:
        if fid not in by_file and len(by_file) >= max_sources:
            continue
        if fid not in by_file:
            summ = db.summary(fid) if hasattr(db, "summary") else None
            if summ:
                by_file[fid] = ["Summary: " + summ[:700]]
                used += min(len(summ), 700)
        if t.startswith("SUMMARY: "):
            continue
        t = t[:1400]
        if used + len(t) > budget:
            continue
        by_file.setdefault(fid, []).append(t)
        used += len(t)
    return by_file


def source_origin(path):
    try:
        from .knowledge import origin
        return origin(path)
    except Exception:
        return "plant"


def source_label(org):
    from .knowledge import ORIGIN_LABEL
    return ORIGIN_LABEL.get(org, "DOCUMENT")


def source_icon(org):
    from .knowledge import ORIGIN_ICON
    return ORIGIN_ICON.get(org, "")


def cache_key(*parts) -> str:
    import hashlib
    norm = " | ".join(re.sub(r"\s+", " ", re.sub(r"[?!.,;:'\"()¿¡。，？！]+", " ", str(p).lower())).strip() for p in parts)
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


def prepare_attachments(paths: list[str], cfg: dict) -> list[dict]:
    """Reads attached files: text (with OCR for pictures/scans) + a resized JPEG for pictures."""
    import base64
    import io
    import os
    from .extract import IMAGE_EXTS, extract
    out = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower().lstrip(".")
        ex = extract(p, cfg)
        item = {"name": os.path.basename(p), "path": p, "text": ex.text or "", "image": None,
                "note": ex.error}
        if ext in IMAGE_EXTS:
            try:
                from PIL import Image, ImageOps
                with Image.open(p) as im:
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((1600, 1600))
                    buf = io.BytesIO()
                    im.save(buf, "JPEG", quality=85)
                    item["image"] = base64.b64encode(buf.getvalue()).decode()
            except Exception as e:
                item["note"] = f"cannot read picture: {e}"
        out.append(item)
    return out


def answer(db, ai, question: str, history: list[dict] | None = None, attachments: list[dict] | None = None,
           on_token=None) -> dict:
    import json as _json
    attachments = attachments or []
    key = None
    if not history and not attachments and question.strip():
        key = cache_key("assistant", ai.chat_model_label(), question)
        hit = db.cache_get(key, (getattr(ai, "cfg", None) or {}).get("answer_cache_days", 7)) if hasattr(db, "cache_get") else None
        if hit:
            res = _json.loads(hit)
            res["cached"] = True
            if on_token:
                on_token(res["text"])
            return res
    q = question.strip() or "Analyse the attached file(s): describe what they show and any problem you see."
    probe = q + " " + " ".join(a["text"][:300] for a in attachments)
    srcs = _gather_sources(db, ai, probe)
    if not srcs and not attachments:
        return {"text": "I could not find anything about that in your indexed documents. "
                        "Check that the folder is added in **Folders & index**.", "sources": []}
    sources, blocks, n = [], [], 0
    for a in attachments:
        n += 1
        body = a["text"][:6000] if a["text"] else ("(picture attached — see image)" if a["image"] else "(no text found)")
        blocks.append(f"[{n}] ATTACHED BY USER: {a['name']}\n{body}")
        sources.append((n, None, a["name"], a["path"]))
    for fid, texts in srcs.items():
        r = db.get(fid)
        if r is None:
            continue
        n += 1
        info = ", ".join(x for x in (r["project"], r["dno"] and f"{r['dno']} Rev {r['rev']}", r["lang"]) if x)
        org = source_origin(r["path"])
        blocks.append(f"[{n}] {source_label(org)}: {r['name']} ({info})\n" + "\n…\n".join(texts))
        sources.append((n, fid, source_icon(org) + r["name"], r["path"]))
    msgs = [{"role": "system", "content": SYSTEM_PROMPT + (
        " The user attached files marked ATTACHED BY USER: analyse them first, then relate them to the other sources."
        " For pictures, describe what you see (equipment, damage, text, alarms) before giving causes and checks."
        if attachments else "")}]
    for h in (history or [])[-4:]:
        msgs.append({"role": h["role"], "content": h["content"][:1500]})
    msgs.append({"role": "user", "content": "SOURCES:\n\n" + "\n\n".join(blocks) + f"\n\nQUESTION: {q}"})
    images = [a["image"] for a in attachments if a.get("image")]
    text = ai.chat(msgs, images=images or None, on_token=on_token)
    res = {"text": text, "sources": sources}
    if key and text:
        db.cache_put(key, _json.dumps(res))
    return res


def answer_with_files(db, ai, question, history, paths, cfg, on_token=None):
    return answer(db, ai, question, history, prepare_attachments(paths, cfg) if paths else None, on_token)


# ------------------------------------------------------------------ revisions diff
def diff_texts(old: str, new: str) -> list[tuple[str, str]]:
    """Sentence-level diff → list of ('add'|'del'|'same', sentence)."""
    split = lambda t: [s.strip() for s in re.split(r"(?<=[.;:。])\s+|\n", t or "") if s.strip()]
    a, b = split(old), split(new)
    out = []
    for op in difflib.ndiff(a, b):
        tag, s = op[:2], op[2:]
        if tag == "- ":
            out.append(("del", s))
        elif tag == "+ ":
            out.append(("add", s))
        elif tag == "  ":
            out.append(("same", s))
    return out
