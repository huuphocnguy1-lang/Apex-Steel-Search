"""Export the index for the Android pad app (Apex Steel Pad).

Creates  ApexPad_YYYYMMDD.apexpad  = a zip containing  pad_index.db  (SQLite):
    docs(name, relpath, size, mtime, ext, kind, dtype, project, dno, rev, title, summary, body)
The pad matches each row with the files it finds on the pad (same file name + size, else same name), so it can
search inside documents and show summaries. Rows for files that are not on the pad are still searchable there
("only on laptop").
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import zipfile

SCHEMA = """
CREATE TABLE docs(name TEXT, relpath TEXT, size INTEGER, mtime REAL, ext TEXT, kind TEXT, dtype TEXT, project TEXT,
                  dno TEXT, rev TEXT, title TEXT, summary TEXT, body TEXT);
CREATE TABLE info(key TEXT PRIMARY KEY, value TEXT);
"""


def _relpath(path: str, roots: list[str]) -> str:
    p = os.path.normpath(path)
    for r in roots:
        r = os.path.normpath(r)
        if p.lower().startswith(r.lower() + os.sep):
            return os.path.basename(r) + "/" + p[len(r) + 1:].replace("\\", "/")
    return os.path.basename(p)


def export(db, out_path: str, roots: list[str], text_chars: int = 3000, include_photos: bool = False,
           log=None, progress=None, should_stop=None) -> int:
    log = log or (lambda m: None)
    progress = progress or (lambda i, n, m: None)
    should_stop = should_stop or (lambda: False)
    tmpdir = tempfile.mkdtemp(prefix="apexpad_")
    dbp = os.path.join(tmpdir, "pad_index.db")
    out = sqlite3.connect(dbp)
    out.executescript(SCHEMA)
    kinds = "" if include_photos else "WHERE f.kind != 'photo'"
    rows = db.q(f"SELECT f.id, f.path, f.name, f.size, f.mtime, f.ext, f.kind, f.dtype, f.project, f.dno, f.rev, "
                f"f.title, substr(t.body, 1, {int(text_chars)}) AS body, s.text AS summary FROM files f "
                f"LEFT JOIN texts t ON t.file_id=f.id LEFT JOIN summaries s ON s.file_id=f.id {kinds}")
    n = len(rows)
    log(f"📱 Exporting {n} documents for the pad…")
    batch = []
    for i, r in enumerate(rows):
        if should_stop():
            log("Export stopped.")
            out.close()
            return 0
        batch.append((r["name"], _relpath(r["path"], roots), r["size"], r["mtime"], r["ext"], r["kind"], r["dtype"],
                      r["project"], r["dno"], r["rev"], r["title"], r["summary"], r["body"]))
        if len(batch) >= 2000:
            out.executemany("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
            batch = []
            progress(i + 1, n, "exporting for pad")
    if batch:
        out.executemany("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
    out.executemany("INSERT INTO info VALUES (?,?)", [("created", time.strftime("%Y-%m-%d %H:%M")),
                                                      ("count", str(n)), ("format", "1")])
    out.commit()
    out.close()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(dbp, "pad_index.db")
    os.remove(dbp)
    os.rmdir(tmpdir)
    mb = os.path.getsize(out_path) / 1e6
    log(f"📱 Pad export ready: {out_path} ({n} documents, {mb:.1f} MB). Copy it to the pad and open it in "
        f"Apex Steel Pad → Import laptop index.")
    progress(n, n, "pad export ready")
    return n
