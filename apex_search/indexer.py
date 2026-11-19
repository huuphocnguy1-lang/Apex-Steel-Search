"""Scans watched folders and keeps the index up to date. Only new or changed files are re-read."""
import hashlib
import logging
import os
import time

from . import meta
from .extract import KINDS, SUPPORTED, extract

log = logging.getLogger(__name__)


def file_hash(path: str, size: int) -> str:
    h = hashlib.sha1()
    h.update(str(size).encode())
    with open(path, "rb") as f:
        if size <= 64 * 1024 * 1024:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        else:  # very big files: head + tail is enough to spot copies
            h.update(f.read(8 << 20))
            f.seek(-8 << 20, os.SEEK_END)
            h.update(f.read(8 << 20))
    return h.hexdigest()


class Indexer:
    def __init__(self, db, cfg, ai=None, log_fn=None, progress=None, should_stop=None):
        self.db, self.cfg, self.ai = db, cfg, ai
        self.log = log_fn or (lambda m: log.info(m))
        self.progress = progress or (lambda i, n, msg: None)
        self.should_stop = should_stop or (lambda: False)

    # ------------------------------------------------------------ walking
    def _excluded(self, name: str) -> bool:
        ex = {e.lower() for e in self.cfg.get("excluded_dirs", [])}
        return name.lower() in ex or name.startswith(".") or name.startswith("$")

    def iter_files(self, root: str):
        max_bytes = int(self.cfg.get("max_file_mb", 500)) * 1024 * 1024
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            dirnames[:] = [d for d in dirnames if not self._excluded(d)]
            for fn in filenames:
                if fn.startswith("~$") or fn.startswith("."):
                    continue
                ext = os.path.splitext(fn)[1].lower().lstrip(".")
                if ext not in SUPPORTED:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size > max_bytes:
                    continue
                yield p, st

    def root_of(self, path: str) -> str | None:
        best = None
        for r in self.cfg.enabled_folders() if hasattr(self.cfg, "enabled_folders") else []:
            rp = os.path.normcase(os.path.abspath(r))
            if os.path.normcase(os.path.abspath(path)).startswith(rp + os.sep) and (best is None or len(r) > len(best)):
                best = r
        return best

    def _retry(self, path: str, error: str | None) -> bool:
        """Re-read a file that failed only because a tool was missing, once the tool is available."""
        if not error:
            return False
        if path.lower().endswith(".dwg") and error.startswith("DWG: install"):
            return os.path.isfile(self.cfg.get("oda_path") or "")
        if "not installed" in error:
            return True
        return False

    # ------------------------------------------------------------ scan
    def scan(self, roots: list[str] | None = None) -> dict:
        roots = roots if roots is not None else self.cfg.enabled_folders()
        t0 = time.time()
        self.log(f"Scanning {len(roots)} folder(s)…")
        known = self.db.file_states()
        found, todo = set(), []
        for root in roots:
            for p, st in self.iter_files(root):
                if self.should_stop():
                    self.log("Scan stopped.")
                    return {"stopped": True}
                found.add(p)
                k = known.get(p)
                if not k or abs((k[0] or 0) - st.st_mtime) > 1 or k[1] != st.st_size or self._retry(p, k[2]):
                    todo.append((p, root))
        removed = 0
        norm_roots = [os.path.normcase(os.path.abspath(r)) + os.sep for r in roots]
        all_roots = [os.path.normcase(os.path.abspath(r)) + os.sep for r in self.cfg.enabled_folders()] \
            if hasattr(self.cfg, "enabled_folders") else norm_roots
        for p in known:
            np_ = os.path.normcase(os.path.abspath(p))
            in_scanned = any(np_.startswith(r) for r in norm_roots)
            in_any = any(np_.startswith(r) for r in all_roots)
            if (in_scanned and p not in found) or not in_any:
                self.db.delete_path(p)
                removed += 1
        self.log(f"{len(found)} files found · {len(todo)} new/changed · {removed} removed")
        done = 0
        for i, (p, root) in enumerate(todo, 1):
            if self.should_stop():
                self.log("Indexing stopped (will continue next time).")
                break
            self.progress(i, len(todo), os.path.basename(p))
            if self.index_path(p, root):
                done += 1
        self.progress(len(todo), len(todo), "")
        self.log(f"Index up to date: {done} file(s) indexed in {time.time() - t0:.1f} s")
        return {"found": len(found), "indexed": done, "removed": removed}

    # ------------------------------------------------------------ one file
    def index_path(self, path: str, root: str | None = None) -> bool:
        try:
            st = os.stat(path)
        except OSError:
            self.db.delete_path(path)
            return False
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower().lstrip(".")
        if ext not in SUPPORTED:
            return False
        root = root or self.root_of(path)
        t0 = time.time()
        ex = extract(path, self.cfg)
        try:
            h = file_hash(path, st.st_size)
        except OSError:
            h = None
        text = ex.text
        dno, rev = meta.drawing_number(name, text if ext in ("pdf", "dxf", "dwg") else "")
        kind = KINDS.get(ext, "other")
        if kind == "pdf":
            kind = "drawing" if (dno or ex.large_format) else ("scan" if ex.ocr else "doc")
        title = meta.title_from(name, text, ex.title)
        f = {
            "path": path, "name": name, "ext": ext, "kind": kind, "size": st.st_size, "mtime": st.st_mtime,
            "hash": h, "project": meta.project(path, root, self.cfg.get("project_regex", "")),
            "dno": dno, "rev": rev, "title": title, "lang": meta.language(text),
            "material": meta.material(text), "ocr": 1 if ex.ocr else 0, "phash": ex.phash,
            "pages": ex.pages, "error": ex.error, "indexed_at": time.time(),
        }
        f["tags"] = " ".join(str(x) for x in (f["dno"], f["rev"] and f"Rev {f['rev']}", f["material"],
                                              f["project"], f["lang"], kind) if x)
        self.db.upsert(f, text, meta.chunks(text, title))
        dt = time.time() - t0
        note = f" · {ex.error}" if ex.error else (" · OCR" if ex.ocr else "")
        self.log(f"{'⚠' if ex.error else '✓'} {name} ({dt:.1f} s){note}")
        return True

    def remove_path(self, path: str):
        if self.db.delete_path(path):
            self.log(f"− removed {os.path.basename(path)}")

    # ------------------------------------------------------------ smart index
    def embed_pending(self, quiet: bool = False) -> int:
        """Builds AI vectors for chunks that do not have one yet."""
        if self.ai is None:
            return 0
        import numpy as np
        model = self.ai.embed_key()
        reset = self.db.reset_vectors_not(model)
        if reset:
            self.log(f"Smart index model changed → {reset} passages will be re-processed")
        total = self.db.count_pending()
        if not total:
            if not quiet:
                self.log("Smart index already up to date.")
            return 0
        self.log(f"Building smart index: {total} passages with {model}…")
        done, bs = 0, self.ai.embed_batch_size()
        while not self.should_stop():
            rows = self.db.pending_chunks(bs)
            if not rows:
                break
            try:
                vecs = self.ai.embed([r["text"][:2000] for r in rows])
            except Exception as e:
                self.log(("Smart index paused: " if quiet else "✘ Smart index: ") + str(e))
                break
            items = []
            for r, v in zip(rows, vecs):
                a = np.asarray(v, dtype=np.float32)
                n = float(np.linalg.norm(a)) or 1.0
                items.append((r["id"], (a / n).astype(np.float16).tobytes()))
            self.db.set_vectors(items, model)
            done += len(rows)
            self.progress(done, total, "smart index")
        if done:
            self.log(f"Smart index: {done} passages processed")
        return done
