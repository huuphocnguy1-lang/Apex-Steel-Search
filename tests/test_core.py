import os
import shutil

import pytest

from apex_search import meta, search
from apex_search.config import Config
from apex_search.db import DB
from apex_search.indexer import Indexer


class FakeAI:
    """Deterministic 'embedding' so smart search can be tested without Ollama."""
    CONCEPTS = [["anchor", "base plate", "地脚螺栓", "tige", "column foot", "column base"],
                ["bolt", "torque", "10.9", "螺栓", "serrage", "tight"],
                ["grout", "calage", "灌浆"], ["paint", "coating", "dft"]]

    def embed_key(self):
        return "fake:1"

    def embed_batch_size(self):
        return 8

    def embed(self, texts):
        out = []
        for t in texts:
            t = t.lower()
            out.append([1.0 + sum(t.count(w) for w in c) for c in self.CONCEPTS] + [0.5])
        return out

    cfg = {"answer_cache_days": 7}

    def chat_model_label(self):
        return "fake"

    def chat(self, messages, images=None, on_token=None, deep=None):
        self.last_images = images
        self.calls = getattr(self, "calls", 0) + 1
        if on_token:
            on_token("Bolts M24 ")
            on_token("grade 10.9, torque 1100 Nm [1]")
        return "Bolts M24 grade 10.9, torque 1100 Nm [1]"


@pytest.fixture()
def env(tmp_path):
    docs = tmp_path / "Projects" / "P-2401"
    docs.mkdir(parents=True)
    (docs / "D-2401-S-101_RevB_Column_bases.txt").write_text(
        "Anchor bolts M36 grade 8.8. Base plate 35 mm S355J2. Grout 50 mm.", encoding="utf-8")
    (docs / "D-2401-S-101_RevC_Column_bases.txt").write_text(
        "Anchor bolts M36 grade 8.8. Base plate 40 mm S355J2. Grout 50 mm. Shear key added.", encoding="utf-8")
    (docs / "吊车梁安装技术交底.txt").write_text("高强螺栓 M24 10.9级，终拧扭矩 1100 N·m。", encoding="utf-8")
    (docs / "Note_pieds_de_poteaux.txt").write_text(
        "Les tiges d'ancrage M36 classe 8.8 sont scellées dans le béton avec une platine de 40 mm.", encoding="utf-8")
    import docx
    d = docx.Document()
    d.add_paragraph("Method statement crane girders. Preload bolts M24 HV 10.9 to 1100 Nm.")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Torque", "1100 Nm"
    d.save(docs / "MS-007_Method_statement.docx")
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.append(["Item", "Grade", "Qty"])
    wb.active.append(["M24 x 90 HV bolt", "10.9", 384])
    wb.save(docs / "BOM_bolts.xlsx")
    dl = tmp_path / "Downloads"
    dl.mkdir()
    shutil.copy(docs / "D-2401-S-101_RevC_Column_bases.txt", dl / "copy_of_column_bases.txt")

    cfg = Config(tmp_path / "settings.json")
    cfg["folders"] = [{"path": str(tmp_path / "Projects"), "enabled": True},
                      {"path": str(dl), "enabled": True}]
    cfg["ocr_enabled"] = False
    db = DB(tmp_path / "index.db")
    ai = FakeAI()
    ix = Indexer(db, cfg, ai)
    ix.scan()
    return db, cfg, ai, ix, tmp_path


def test_drawing_number_parsing():
    assert meta.drawing_number("D-2401-S-101_RevC_Column bases.pdf") == ("D-2401-S-101", "C")
    assert meta.drawing_number("ABC-123 rev 02.dwg") == ("ABC-123", "02")
    assert meta.drawing_number("Daily_Report_2026-11-12.docx") == (None, None)
    assert meta.rev_key("B") < meta.rev_key("C")
    assert meta.rev_key("2") < meta.rev_key("10")


def test_tags(env):
    db, *_ = env
    rows = {r["name"]: r for r in db.library_rows()}
    r = rows["D-2401-S-101_RevC_Column_bases.txt"]
    assert r["project"] == "P-2401" and r["rev"] == "C" and r["material"] == "S355J2"
    assert rows["吊车梁安装技术交底.txt"]["lang"] == "中文"
    assert rows["Note_pieds_de_poteaux.txt"]["lang"] == "FR"
    assert db.latest_revs()["D-2401-S-101"] == "C"


def test_keyword_search(env):
    db, *_ = env
    names = [d["name"] for d in search.keyword_search(db, "1100")["results"]]
    assert "MS-007_Method_statement.docx" in names
    assert "吊车梁安装技术交底.txt" in names
    # short Chinese word (2 characters) works
    assert [d["name"] for d in search.keyword_search(db, "螺栓")["results"]] == ["吊车梁安装技术交底.txt"]
    # Excel content is searchable
    assert "BOM_bolts.xlsx" in [d["name"] for d in search.keyword_search(db, "M24 x 90")["results"]]
    # latest revision filter hides Rev B
    res = search.keyword_search(db, "base plate", {"latest": True})["results"]
    assert all(d["rev"] != "B" for d in res)


def test_smart_and_assistant(env):
    db, cfg, ai, ix, _ = env
    assert ix.embed_pending() > 0
    res = search.smart_search(db, ai, "column foot fixing")["results"]
    assert res and any("tige" in (db.body(d["id"]) or "") or "Anchor" in (db.body(d["id"]) or "") for d in res[:3])
    a = search.answer(db, ai, "What torque for M24 10.9 bolts?")
    assert "1100" in a["text"] and a["sources"]


def test_duplicates_and_rescan(env):
    db, cfg, ai, ix, tmp = env
    groups = db.duplicate_groups()
    assert len(groups) == 1 and len(groups[0]) == 2
    os.remove(tmp / "Downloads" / "copy_of_column_bases.txt")
    ix.scan()
    assert db.duplicate_groups() == []


def test_diff():
    d = search.diff_texts("Base plate 35 mm. Grout 50 mm.", "Base plate 40 mm. Grout 50 mm.")
    assert ("del", "Base plate 35 mm.") in d and ("add", "Base plate 40 mm.") in d


def test_dwg_retried_when_converter_installed(env):
    db, cfg, ai, ix, tmp = env
    dwg = tmp / "Projects" / "P-2401" / "D-2401-S-300_RevA.dwg"
    dwg.write_bytes(b"AC1027 fake")
    cfg["oda_path"] = str(tmp / "missing.exe")
    ix.scan()
    r = [x for x in db.library_rows() if x["name"] == dwg.name][0]
    assert r["error"].startswith("DWG: install")
    fake = tmp / "ODAFileConverter.exe"
    fake.write_text("x")
    cfg["oda_path"] = str(fake)
    assert ix._retry(str(dwg), r["error"]) is True


def test_assistant_with_attachment(env, tmp_path):
    db, cfg, ai, ix, _ = env
    note = tmp_path / "site_note.txt"
    note.write_text("Stopper rod at 80 %, argon flow 5 l/min, mould level hunting.", encoding="utf-8")
    from PIL import Image
    img = tmp_path / "hmi.png"
    Image.new("RGB", (64, 48), "red").save(img)
    a = search.answer_with_files(db, ai, "", [], [str(note), str(img)], cfg)
    assert a["sources"][0][2] == "site_note.txt" and a["sources"][0][1] is None
    assert ai.last_images and len(ai.last_images) == 1


# ---------------------------------------------------------------- v0.3.0
def test_doctype():
    from apex_search import doctype
    mech = "SECTION A-A  DETAIL B  SCALE 1:10  General tolerances ISO 2768-m  Ra 3.2  Material S355J2  Weight 42 kg  Ø120 H7"
    hyd = "HPU hydraulic power unit. Pump P1 71 cm3, relief valve 210 bar, accumulator 32 l, servo valve SV1, Y1 Y2 Y3, 60 l/min, tank, filter"
    pid = "P&ID cooling water  PT-101  FIC-205  LV-12  TT-301  DN150 PN16  6\"-CW-1023  control valve"
    ele = "MCC panel  400 VAC  24 VDC  contactor K1  -Q1 circuit breaker  X1:3  terminal  cable 4x2.5 mm²  PLC I/O"
    assert doctype.classify("a.pdf", "pdf", "drawing", mech) == "mechanical"
    assert doctype.classify("b.pdf", "pdf", "drawing", hyd) == "hydraulic"
    assert doctype.classify("c.pdf", "pdf", "drawing", pid) == "pid"
    assert doctype.classify("d.dwg", "dwg", "drawing", ele) == "electrical"
    assert doctype.classify("e.docx", "docx", "doc", "Daily report: weather sunny, grouting done.") == "document"
    assert doctype.classify("f.jpg", "jpg", "photo", "") == "photo"


def test_classify_existing_and_filter(env):
    db, cfg, ai, ix, _ = env
    db.set_dtypes([(None, r["id"]) for r in db.library_rows()])
    assert ix.classify_existing() > 0
    assert all(r["dtype"] for r in db.library_rows())
    res = search.keyword_search(db, "base plate", {"kind": "t:hydraulic"})["results"]
    assert res == []


def test_cases_and_specialist(env, tmp_path):
    from apex_search import specialist
    db, cfg, ai, ix, _ = env
    cid = db.case_save({"date": "2026-11-15", "area": "Caster", "symptom": "Mould level hunting, stopper rod at 80 %",
                        "cause": "SEN clogging, argon flow dropped", "fix": "SEN changed"})
    assert db.cases("stopper")[0]["id"] == cid
    assert db.similar_cases("stopper rod rising mould level hunting", "Caster")[0]["id"] == cid
    a = specialist.specialist_answer(db, ai, "Caster", "Mould level hunting and stopper rod rising")
    assert any("Lesson learned" in s[2] for s in a["sources"])
    t = specialist.casting_temperatures({"C": 0.05, "Mn": 0.2, "Al": 0.03}, 25, 38)
    assert 1528 < t["liquidus"] < 1534 and abs(t["tundish"] - t["liquidus"] - 25) < 1e-9
    db.case_delete(cid)
    assert db.cases() == []


def test_iba_csv_events(tmp_path):
    import numpy as np
    from apex_search import iba
    t = np.arange(0, 120, 0.25)
    rnd = np.random.default_rng(1)
    argon = 9 - 4 * np.clip((t - 38) / 36, 0, 1) + rnd.normal(0, 0.07, len(t))
    stopper = 52 + 27 * np.clip((t - 44) / 36, 0, 1) + rnd.normal(0, 0.25, len(t))
    level = rnd.normal(0, 0.35, len(t)) + np.sin(t * 2 * np.pi * 0.33) * np.clip((t - 66) * 0.9, 0, 12)
    p = tmp_path / "cc1_export.csv"
    with open(p, "w") as f:
        f.write("Time;Argon flow;Stopper position;Mould level\n s;l/min;%;mm\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.2f};{argon[i]:.3f};{stopper[i]:.3f};{level[i]:.3f}\n".replace(".", ","))
    rec = iba.load(str(p))
    assert [s.name for s in rec.signals] == ["Argon flow", "Stopper position", "Mould level"]
    assert rec.signals[0].unit == "l/min" and abs(rec.t[-1] - 119.75) < 1e-6
    ev = iba.analyse(rec)
    assert ev[0]["signal"] == "Argon flow" and ev[0]["dir"] == "down"
    assert {e["signal"]: e["type"] for e in ev}["Mould level"] == "oscillation"
    assert "first" in iba.events_text(rec, ev)
    td, vd = iba.decimate(rec.t, rec.signals[2].v, 50)
    assert len(vd) <= 2 * 50 + 2


def test_hydraulics():
    from apex_search import hydraulics as h
    c = h.cylinder(125, 70, 160, 60)
    assert 195 < c["push_kN"] < 197 and c["pull_kN"] < c["push_kN"]
    assert abs(h.pump(71, 1480, 160)["flow_lmin"] - 99.8) < 0.2
    assert h.accumulator(32, 90, 120, 160)["usable_l"] > 3
    assert h.accumulator(32, 130, 120, 160)["usable_l"] == 0
    words = [(10, 10, 30, 20, "SV1"), (10, 30, 40, 40, "160"), (45, 30, 60, 40, "bar"), (300, 300, 320, 310, "S355")]
    comps = h.components_from_words(words)
    assert [c["tag"] for c in comps] == ["SV1"] and comps[0]["values"] == ["160 bar"]


def test_iba_dat_layouts_join_scan(tmp_path):
    import datetime as dt
    import numpy as np
    from apex_search import iba
    n = 400
    a = np.r_[np.full(200, 5.0), np.full(200, 9.0)] + np.random.default_rng(2).normal(0, 0.01, n)
    # layout 1: dict name -> list, single interval
    r1 = iba._from_decoded("a.dat", "2026-08-24T12:56:00", 0.1, {"Speed [m/min]": a.tolist(), "B": [1.0] * n})
    assert r1.signals[0].name == "Speed" and r1.signals[0].unit == "m/min" and abs(r1.t[-1] - 39.9) < 1e-6
    assert r1.start == dt.datetime(2026, 8, 24, 12, 56)
    # layout 2: dict name -> {values, unit, interval} with different rates
    r2 = iba._from_decoded("b.dat", dt.datetime(2026, 8, 24, 12, 59), None,
                           {"Speed": {"values": a.tolist(), "unit": "m/min", "interval": 0.1},
                            "Slow": {"values": [1.0] * 40, "interval": 1.0}})
    assert len(r2.signals[1].v) == n
    j = iba.join([r2, r1])
    assert len(j.t) == 2 * n and j.t[0] == 0 and j.t[-1] > 180
    rows = iba.scan_files([r1, r2])
    assert rows[0]["first"] == "Speed" and rows[0]["events"] >= 1
    try:
        iba.load_dat(str(tmp_path / "x.dat"))
    except ValueError as e:
        assert "ASCII" in str(e)


def test_answer_cache_and_summaries(tmp_path):
    from apex_search import search
    from apex_search.db import DB
    db = DB(str(tmp_path / "c.db"))
    k1 = search.cache_key("assistant", "m", "Pump pressure ?")
    k2 = search.cache_key("assistant", "m", "pump   pressure?")
    assert k1 == k2
    db.cache_put(k1, '{"text": "x", "sources": []}')
    assert db.cache_get(k2, 7)
    db.cache_clear()
    assert db.cache_get(k2, 7) is None
    assert db.count_to_summarise([]) == (0, 0)


# ------------------------------------------------------------------ knowledge library (v0.5)
def test_knowledge_builtin_origin_and_html(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_SEARCH_HOME", str(tmp_path))
    from apex_search import knowledge
    n = knowledge.install_builtin()
    files = knowledge.builtin_files()
    assert n >= 10 and len(files) >= 10
    assert any("Pendulum" in f for f in files) and any("Hydraulic" in f for f in files)
    assert knowledge.install_builtin() == 0          # unchanged → not copied again
    assert knowledge.origin(files[0]) == "builtin"
    assert knowledge.origin(os.path.join(knowledge.root(), "web", "ESP", "x.md")) == "web"
    assert knowledge.origin(os.path.join(knowledge.root(), "my_notes", "x.md")) == "plant"
    assert knowledge.origin(str(tmp_path / "elsewhere.pdf")) == "plant"
    txt, title = knowledge.html_to_text("<html><title>HGC</title><nav>menu</nav><script>x()</script>"
                                        "<h2>Servo valve null</h2><p>" + "The servo valve null shift makes the HGC cylinder drift. " * 5 + "</p></html>")
    assert title == "HGC" and "## Servo valve null" in txt and "menu" not in txt and "x()" not in txt


def test_knowledge_learn_with_fake_web(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_SEARCH_HOME", str(tmp_path))
    from apex_search import knowledge
    page = ("<html><title>Pendulum shear basics</title><body><p>" +
            "The pendulum shear cuts the transfer bar in hot rolling; knife clearance and cut timing matter. " * 40 +
            "</p></body></html>")
    junk_serp = ('<li class="b_algo"><h2><a href="https://fabricsnap.com/">AI fabric identifier</a></h2><p>Find a fabric by photo</p></li>'
                 '<li class="b_algo"><h2><a href="https://www.yahoo.com/news/">Yahoo News</a></h2><p>Latest news</p></li>')
    good_serp = ('<li class="b_algo"><h2><a href="https://example.com/ps">Pendulum shear in hot rolling mills</a></h2>'
                 '<p>How the pendulum shear cuts the transfer bar</p></li>'
                 '<li class="b_algo"><h2><a href="https://www.youtube.com/watch?v=1">Pendulum shear video</a></h2><p>shear</p></li>')
    seen = []

    def fake_get(url, limit=15_000_000, timeout=20):
        seen.append(url)
        if "cn.bing.com/search" in url:        # 'Bing International' gives junk (like in the field)
            return junk_serp.encode(), "text/html"
        if "www.bing.com/search" in url:
            return good_serp.encode(), "text/html"
        if url.endswith("/ps"):
            return page.encode(), "text/html; charset=utf-8"
        raise OSError("blocked")
    monkeypatch.setattr(knowledge, "_get", fake_get)
    logs = []
    n = knowledge.learn(["PS"], per_query=2, wikipedia=True, log=logs.append)
    assert n == 1                                    # junk never fetched; same good page saved once
    assert not any("fabricsnap" in u or "yahoo" in u for u in seen if "search" not in u)
    assert any("none about this topic" in l for l in logs)
    assert sum("Wikipedia not reachable" in l for l in logs) == 1   # dead source tried only once
    m = knowledge.load_manifest()
    e = list(m.values())[0]
    assert e["topic"] == "PS" and "Source: https://example.com/ps" in open(e["file"], encoding="utf-8").read()
    assert knowledge.counts_by_topic() == {"PS": 1}
    knowledge.remove_source(list(m)[0])
    assert knowledge.load_manifest() == {} and not os.path.exists(e["file"])


def test_result_relevance():
    from apex_search import knowledge as k
    q = "thin slab caster funnel mould oscillation"
    assert not k.result_relevant(q, "RainSFM wiki fandom")
    assert not k.result_relevant(q, "AI fabric identifier find a fabric by photo")
    assert k.result_relevant(q, "Funnel mould for thin slab casters: oscillation and heat flux")


def test_answer_labels_sources_by_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_SEARCH_HOME", str(tmp_path / "home"))
    from apex_search import knowledge
    knowledge.install_builtin()
    plant = tmp_path / "plant"
    plant.mkdir()
    (plant / "bolt_spec.txt").write_text("Anchor bolt torque 10.9 grade M24 tightening 600 Nm. " * 10, encoding="utf-8")
    cfg = Config(str(tmp_path / "cfg.json"))
    cfg["folders"] = [{"path": str(plant), "enabled": True}]
    db = DB(str(tmp_path / "i.db"))

    class KAI(FakeAI):
        def embed(self, texts):
            return [[1.0 if "anchor" in t.lower() else 0.0, 0.2] for t in texts]
    ai = KAI()
    ix = Indexer(db, cfg, ai)
    ix.scan()
    ix.embed_pending()
    roots = cfg.enabled_folders()
    assert knowledge.root() in roots                 # knowledge folder is indexed automatically
    res = search.answer(db, ai, "anchor bolt torque")
    names = [s[2] for s in res["sources"]]
    assert names and names[0].startswith("🏭")      # plant document first, labelled
    assert any(n.startswith("📘") for n in names)    # built-in expert notes also used


def test_search_link_cleaning():
    import base64, urllib.parse
    from apex_search import knowledge
    real = "https://www.example.org/hydraulics/servo-valve.pdf"
    enc = "a1" + base64.urlsafe_b64encode(real.encode()).decode().rstrip("=")
    assert knowledge._clean_link("https://www.bing.com/ck/a?!&amp;&amp;p=abc&amp;u=" + enc + "&amp;ntb=1") == real
    assert knowledge._clean_link("//duckduckgo.com/l/?uddg=" + urllib.parse.quote(real)) == real
    assert knowledge._clean_link("https://www.youtube.com/watch?v=1") is None


def test_summary_plan_skips_drawings_old_revisions_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_SEARCH_HOME", str(tmp_path / "home"))
    db = DB(str(tmp_path / "p.db"))
    root = str(tmp_path / "proj")
    text = "Hydraulic servo valve maintenance and commissioning text. " * 40   # > 300 chars
    def add(name, body=text, **kw):
        f = {"path": os.path.join(root, name), "name": name, "ext": name.rsplit(".", 1)[1], "kind": "doc",
             "mtime": 1000.0, "pages": 10, "hash": name}
        f.update(kw)
        return db.upsert(f, body, [])
    d1 = add("GA_drawing_sheet.pdf", kind="drawing", pages=1, dno="D-100", rev="A")
    cad = add("frame.dwg", kind="drawing", pages=1)
    old = add("Spec_P-200_revA.pdf", dno="P-200", rev="A")
    new = add("Spec_P-200_revB.pdf", dno="P-200", rev="B")
    dup1 = add("report_copy1.pdf", hash="same")
    dup2 = add("report_copy2.pdf", hash="same")
    man = add("Operating_Manual_HPU.pdf", mtime=500.0)
    big = add("Long_document_with_number.pdf", body=text * 4, kind="drawing", pages=40, dno="D-300", rev="0")
    todo, done, total = db.summary_plan([root])
    assert d1 not in todo and cad not in todo                # drawing sheets skipped
    assert old not in todo and new in todo                   # latest revision only
    assert (dup1 in todo) != (dup2 in todo)                  # one copy of duplicates
    assert big in todo                                       # multi-page text document kept even if tagged drawing
    assert todo[0] == man                                    # manuals first (even if older)
    assert done == 0 and total == len(todo)
    todo_all, _, _ = db.summary_plan([root], skip_drawings=False, latest_only=False)
    assert d1 in todo_all and old in todo_all and dup1 in todo_all and dup2 in todo_all
    db.save_summary(man, "summary", "m")
    assert db.count_to_summarise([root]) == (1, total)


def test_pad_export(tmp_path):
    import sqlite3, zipfile
    from apex_search import padexport
    db = DB(str(tmp_path / "x.db"))
    root = str(tmp_path / "C_PEYI Zhongshou ESP")
    fid = db.upsert({"path": os.path.join(root, "DWG", "A_115-F0302_ZSZ001_R00.pdf"), "name": "A_115-F0302_ZSZ001_R00.pdf",
                     "ext": "pdf", "kind": "drawing", "size": 1234, "mtime": 1.0, "dno": "115-F0302", "rev": "R00",
                     "title": "HPU piping"}, "Hydraulic power unit piping " * 300, [])
    db.save_summary(fid, "HPU piping drawing", "m")
    out = str(tmp_path / "t.apexpad")
    assert padexport.export(db, out, [root]) == 1
    z = zipfile.ZipFile(out)
    z.extract("pad_index.db", str(tmp_path))
    c = sqlite3.connect(str(tmp_path / "pad_index.db"))
    r = c.execute("SELECT name, relpath, dno, rev, title, summary, length(body) FROM docs").fetchone()
    assert r[1] == "C_PEYI Zhongshou ESP/DWG/A_115-F0302_ZSZ001_R00.pdf" and r[2] == "115-F0302" and r[5] == "HPU piping drawing"
    assert r[6] == 3000
