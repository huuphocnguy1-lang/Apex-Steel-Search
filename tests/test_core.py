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

    def chat(self, messages, images=None):
        self.last_images = images
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
