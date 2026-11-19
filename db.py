"""SQLite index: file metadata, full-text index (FTS5 trigram: works for Chinese too) and AI vectors."""
import os
import sqlite3
import threading
from collections import defaultdict

from .meta import rev_key

FILE_COLS = ["path", "name", "ext", "kind", "size", "mtime", "hash", "project", "dno", "rev", "title",
             "lang", "material", "ocr", "phash", "pages", "error", "indexed_at", "tags", "dtype"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
  id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT, ext TEXT, kind TEXT, size INTEGER, mtime REAL,
  hash TEXT, project TEXT, dno TEXT, rev TEXT, title TEXT, lang TEXT, material TEXT, ocr INTEGER DEFAULT 0,
  phash TEXT, pages INTEGER, error TEXT, indexed_at REAL, tags TEXT);
CREATE INDEX IF NOT EXISTS ix_files_hash ON files(hash);
CREATE INDEX IF NOT EXISTS ix_files_dno ON files(dno);
CREATE INDEX IF NOT EXISTS ix_files_kind ON files(kind);
CREATE TABLE IF NOT EXISTS texts(file_id INTEGER PRIMARY KEY, body TEXT);
CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, file_id INTEGER, idx INTEGER, text TEXT, vec BLOB, model TEXT);
CREATE INDEX IF NOT EXISTS ix_chunks_file ON chunks(file_id);
CREATE INDEX IF NOT EXISTS ix_chunks_vec ON chunks(model);
CREATE TABLE IF NOT EXISTS cases(id INTEGER PRIMARY KEY, date TEXT, area TEXT, symptom TEXT, cause TEXT, fix TEXT,
  author TEXT, created REAL);
"""


class DB:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.version = 0          # bumps when vectors/files change (invalidates caches)
        self._vcache = None
        self._init()

    def _init(self):
        c = self.conn
        c.executescript(SCHEMA)
        cols = {r[1] for r in c.execute("PRAGMA table_info(files)")}
        if "dtype" not in cols:   # upgrade from v0.1/v0.2: keep the existing index
            c.execute("ALTER TABLE files ADD COLUMN dtype TEXT")
        c.execute("CREATE INDEX IF NOT EXISTS ix_files_dtype ON files(dtype)")
        try:
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(name, title, body, tags, tokenize='trigram')")
        except sqlite3.OperationalError:
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(name, title, body, tags)")
        sql = c.execute("SELECT sql FROM sqlite_master WHERE name='fts'").fetchone()[0]
        self.trigram = "trigram" in sql
        c.commit()

    def close(self):
        with self.lock:
            self.conn.close()

    # ------------------------------------------------------------ generic
    def q(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).fetchone()

    # ------------------------------------------------------------ files
    def upsert(self, f: dict, body: str, chunks: list[str]) -> int:
        vals = [f.get(k) for k in FILE_COLS]
        with self.lock, self.conn as c:
            r = c.execute("SELECT id FROM files WHERE path=?", (f["path"],)).fetchone()
            if r:
                fid = r[0]
                c.execute(f"UPDATE files SET {','.join(k + '=?' for k in FILE_COLS)} WHERE id=?", vals + [fid])
                c.execute("DELETE FROM fts WHERE rowid=?", (fid,))
                c.execute("DELETE FROM chunks WHERE file_id=?", (fid,))
            else:
                cur = c.execute(f"INSERT INTO files({','.join(FILE_COLS)}) VALUES({','.join('?' * len(FILE_COLS))})", vals)
                fid = cur.lastrowid
            c.execute("INSERT OR REPLACE INTO texts(file_id, body) VALUES(?,?)", (fid, body))
            c.execute("INSERT INTO fts(rowid,name,title,body,tags) VALUES(?,?,?,?,?)",
                      (fid, f.get("name") or "", f.get("title") or "", body, f.get("tags") or ""))
            c.executemany("INSERT INTO chunks(file_id,idx,text) VALUES(?,?,?)",
                          [(fid, i, t) for i, t in enumerate(chunks)])
            self.version += 1
        return fid

    def delete_path(self, path: str) -> bool:
        with self.lock, self.conn as c:
            r = c.execute("SELECT id FROM files WHERE path=?", (path,)).fetchone()
            if not r:
                return False
            fid = r[0]
            for sql in ("DELETE FROM files WHERE id=?", "DELETE FROM texts WHERE file_id=?",
                        "DELETE FROM fts WHERE rowid=?", "DELETE FROM chunks WHERE file_id=?"):
                c.execute(sql, (fid,))
            self.version += 1
        return True

    def file_states(self) -> dict[str, tuple[float, int, str | None]]:
        return {r["path"]: (r["mtime"], r["size"], r["error"]) for r in self.q("SELECT path, mtime, size, error FROM files")}

    def get(self, fid):
        return self.one("SELECT * FROM files WHERE id=?", (fid,))

    def body(self, fid) -> str:
        r = self.one("SELECT body FROM texts WHERE file_id=?", (fid,))
        return r[0] if r and r[0] else ""

    def rows_with_body(self, ids) -> list:
        ids = list(ids)
        out = []
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            out += self.q(f"SELECT f.*, t.body FROM files f LEFT JOIN texts t ON t.file_id=f.id "
                          f"WHERE f.id IN ({','.join('?' * len(part))})", part)
        return out

    def projects(self) -> list[str]:
        return [r[0] for r in self.q("SELECT DISTINCT project FROM files WHERE project IS NOT NULL ORDER BY project")]

    def latest_revs(self) -> dict[str, str]:
        best = {}
        for r in self.q("SELECT dno, rev FROM files WHERE dno IS NOT NULL AND rev IS NOT NULL"):
            if r["dno"] not in best or rev_key(r["rev"]) > rev_key(best[r["dno"]]):
                best[r["dno"]] = r["rev"]
        return best

    def library_rows(self, text: str = "", limit: int = 5000):
        if text:
            like = f"%{text}%"
            return self.q("SELECT * FROM files WHERE name LIKE ? OR dno LIKE ? OR project LIKE ? OR title LIKE ? "
                          "ORDER BY mtime DESC LIMIT ?", (like, like, like, like, limit))
        return self.q("SELECT * FROM files ORDER BY mtime DESC LIMIT ?", (limit,))

    def revision_groups(self, text: str = ""):
        like = f"%{text}%"
        return self.q("SELECT dno, COUNT(DISTINCT rev) AS nrev, COUNT(*) AS nfiles, MAX(title) AS title "
                      "FROM files WHERE dno IS NOT NULL AND (dno LIKE ? OR title LIKE ?) "
                      "GROUP BY dno ORDER BY dno", (like, like))

    def revisions(self, dno: str):
        rows = self.q("SELECT * FROM files WHERE dno=?", (dno,))
        return sorted(rows, key=lambda r: (rev_key(r["rev"]), r["mtime"] or 0))

    def photos(self, text: str = "", limit: int = 400):
        if text:
            like = f"%{text}%"
            return self.q("SELECT f.* FROM files f LEFT JOIN texts t ON t.file_id=f.id WHERE f.kind='photo' "
                          "AND (f.name LIKE ? OR t.body LIKE ? OR f.project LIKE ?) ORDER BY f.mtime DESC LIMIT ?",
                          (like, like, like, limit))
        return self.q("SELECT * FROM files WHERE kind='photo' ORDER BY mtime DESC LIMIT ?", (limit,))

    def all_photo_hashes(self):
        return self.q("SELECT id, phash FROM files WHERE kind='photo' AND phash IS NOT NULL")

    def duplicate_groups(self):
        groups = defaultdict(list)
        for r in self.q("SELECT * FROM files WHERE hash IN (SELECT hash FROM files WHERE hash IS NOT NULL "
                        "GROUP BY hash HAVING COUNT(*)>1) ORDER BY hash, mtime"):
            groups[r["hash"]].append(r)
        return list(groups.values())

    def stats(self) -> dict:
        s = {"total": self.one("SELECT COUNT(*) FROM files")[0]}
        for r in self.q("SELECT kind, COUNT(*) n FROM files GROUP BY kind"):
            s[r["kind"]] = r["n"]
        s["ocr"] = self.one("SELECT COUNT(*) FROM files WHERE ocr=1")[0]
        s["errors"] = self.one("SELECT COUNT(*) FROM files WHERE error IS NOT NULL")[0]
        s["chunks"] = self.one("SELECT COUNT(*) FROM chunks")[0]
        s["vectors"] = self.one("SELECT COUNT(*) FROM chunks WHERE vec IS NOT NULL")[0]
        try:
            s["db_mb"] = round(sum(os.path.getsize(self.path + x) for x in ("", "-wal") if os.path.exists(self.path + x)) / 1e6, 1)
        except OSError:
            s["db_mb"] = 0
        return s

    # ------------------------------------------------------------ drawing types
    def untyped(self, limit: int = 2000):
        return self.q("SELECT f.id, f.name, f.ext, f.kind, t.body FROM files f LEFT JOIN texts t ON t.file_id=f.id "
                      "WHERE f.dtype IS NULL LIMIT ?", (limit,))

    def set_dtypes(self, items: list[tuple[str, int]]):
        with self.lock, self.conn as c:
            c.executemany("UPDATE files SET dtype=? WHERE id=?", items)

    def dtype_counts(self) -> dict:
        return {r[0]: r[1] for r in self.q("SELECT dtype, COUNT(*) FROM files GROUP BY dtype")}

    def files_by_dtype(self, dtype: str, text: str = "", limit: int = 2000):
        like = f"%{text}%"
        return self.q("SELECT * FROM files WHERE dtype=? AND (name LIKE ? OR title LIKE ? OR project LIKE ?) "
                      "ORDER BY mtime DESC LIMIT ?", (dtype, like, like, like, limit))

    # ------------------------------------------------------------ lessons learned
    def cases(self, text: str = ""):
        if text:
            like = f"%{text}%"
            return self.q("SELECT * FROM cases WHERE area LIKE ? OR symptom LIKE ? OR cause LIKE ? OR fix LIKE ? "
                          "ORDER BY date DESC, id DESC", (like, like, like, like))
        return self.q("SELECT * FROM cases ORDER BY date DESC, id DESC")

    def case_save(self, d: dict) -> int:
        import time
        with self.lock, self.conn as c:
            if d.get("id"):
                c.execute("UPDATE cases SET date=?, area=?, symptom=?, cause=?, fix=?, author=? WHERE id=?",
                          (d["date"], d["area"], d["symptom"], d["cause"], d["fix"], d.get("author", ""), d["id"]))
                return d["id"]
            cur = c.execute("INSERT INTO cases(date, area, symptom, cause, fix, author, created) VALUES(?,?,?,?,?,?,?)",
                            (d["date"], d["area"], d["symptom"], d["cause"], d["fix"], d.get("author", ""), time.time()))
            return cur.lastrowid

    def case_delete(self, cid: int):
        with self.lock, self.conn as c:
            c.execute("DELETE FROM cases WHERE id=?", (cid,))

    def similar_cases(self, text: str, area: str | None = None, k: int = 3):
        import re as _re
        words = {w for w in _re.findall(r"[\w\u4e00-\u9fff]{3,}", (text or "").lower())}
        if not words:
            return []
        scored = []
        for r in self.q("SELECT * FROM cases"):
            hay = f"{r['symptom']} {r['cause']} {r['fix']}".lower()
            s = sum(1 for w in words if w in hay) + (1.5 if area and r["area"] == area else 0)
            if s >= 2:
                scored.append((s, r))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:k]]

    # ------------------------------------------------------------ vectors
    def reset_vectors_not(self, model: str):
        with self.lock, self.conn as c:
            n = c.execute("UPDATE chunks SET vec=NULL, model=NULL WHERE model IS NOT NULL AND model<>?", (model,)).rowcount
            if n:
                self.version += 1
        return n

    def pending_chunks(self, limit: int = 64):
        return self.q("SELECT id, text FROM chunks WHERE vec IS NULL ORDER BY id LIMIT ?", (limit,))

    def count_pending(self) -> int:
        return self.one("SELECT COUNT(*) FROM chunks WHERE vec IS NULL")[0]

    def set_vectors(self, items: list[tuple[int, bytes]], model: str):
        with self.lock, self.conn as c:
            c.executemany("UPDATE chunks SET vec=?, model=? WHERE id=?", [(v, model, i) for i, v in items])
            self.version += 1

    def vector_matrix(self, model: str):
        """Returns (matrix float16 [n, d] normalised, chunk_ids, file_ids) or (None, [], [])."""
        import numpy as np
        if self._vcache and self._vcache[0] == (model, self.version):
            return self._vcache[1]
        rows = self.q("SELECT id, file_id, vec FROM chunks WHERE model=? AND vec IS NOT NULL", (model,))
        if not rows:
            res = (None, [], [])
        else:
            mat = np.vstack([np.frombuffer(r["vec"], dtype=np.float16) for r in rows])
            res = (mat, [r["id"] for r in rows], [r["file_id"] for r in rows])
        self._vcache = ((model, self.version), res)
        return res

    def chunk_texts(self, ids) -> dict[int, str]:
        ids = list(ids)
        if not ids:
            return {}
        return {r["id"]: r["text"] for r in self.q(f"SELECT id, text FROM chunks WHERE id IN ({','.join('?' * len(ids))})", ids)}
