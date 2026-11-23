"""Scans watched folders and keeps the index up to date. Only new or changed files are re-read."""
import hashlib
import logging
import os
import time

from . import doctype, meta
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
    def __init__(self, db, cfg, ai=None, log_fn=None, progress=None, should_stop=None, paused=None):
        self.db, self.cfg, self.ai = db, cfg, ai
        self.log = log_fn or (lambda m: log.info(m))
        self.progress = progress or (lambda i, n, msg: None)
        self.should_stop = should_stop or (lambda: False)
        self.paused = paused or (lambda: False)

    def _wait_if_paused(self):
        """Background AI work gives way while you are asking a question (or using the laptop at night)."""
        while self.paused() and not self.should_stop():
            time.sleep(1.0)

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
        f["dtype"] = doctype.classify(name, ext, kind, text, ex.large_format)
        f["tags"] = " ".join(str(x) for x in (f["dno"], f["rev"] and f"Rev {f['rev']}", f["material"],
                                              f["project"], f["lang"], kind,
                                              doctype.LABELS.get(f["dtype"], "")) if x)
        self.db.upsert(f, text, meta.chunks(text, title))
        dt = time.time() - t0
        note = f" · {ex.error}" if ex.error else (" · OCR" if ex.ocr else "")
        self.log(f"{'⚠' if ex.error else '✓'} {name} ({dt:.1f} s){note}")
        return True

    # ------------------------------------------------------------ night analysis: pre-summaries
    SUMMARY_SYSTEM = ("You summarise steel-plant documents for engineers. Write at most 90 words in English: what the "
                      "document is and its main content. Then one line starting with 'Key facts:' listing equipment, "
                      "tags, values with units, problems and dates found in the text. Use only the given text.")

    SUMMARY_SHORT = ("Summarise this steel-plant document for engineers in at most 60 words of English: what it is and "
                     "its main content. Then one line 'Key facts:' with equipment, tags, values with units, problems, "
                     "dates. Use only the given text.")

    def _summary_model(self) -> str | None:
        """Small fast model for summaries (Settings). Falls back to the chat model when not installed."""
        if self.ai.online:
            return (self.cfg.get("summary_model_cloud") or "").strip() or None
        m = (self.cfg.get("summary_model_local") or "").strip()
        if not m:
            return None
        if hasattr(self.ai, "has_local_model") and not self.ai.has_local_model(m):
            self.log(f"Summary model '{m}' is not installed → using the chat model (slower). "
                     f"Install it in Settings → Night analysis, or run:  ollama pull {m}")
            return None
        return m

    def summarize_pending(self, folders: list[str]) -> int:
        if self.ai is None or not folders:
            return 0
        skip_dr = bool(self.cfg.get("sum_skip_drawings", True))
        latest = bool(self.cfg.get("sum_latest_rev_only", True))
        short = bool(self.cfg.get("sum_short", True))
        plan, done0, total = self.db.summary_plan(folders, skip_dr, latest)
        if not plan:
            self.log(f"Night analysis: all {total} selected documents are already summarised.")
            return 0
        model = self._summary_model()
        label = model or self.ai.chat_model_label()
        self.log(f"Night analysis: {len(plan)} documents to summarise"
                 + (" (drawing sheets skipped" if skip_dr else " (drawings included")
                 + (", older revisions & duplicates skipped)" if latest else ")")
                 + f" · model {label} · {'short' if short else 'full'} summaries · most useful first.")
        system = self.SUMMARY_SHORT if short else self.SUMMARY_SYSTEM
        limit = 3000 if short else 6000
        done, t0, gpu_logged = 0, time.time(), False
        for fid in plan:
            if self.should_stop():
                break
            self._wait_if_paused()
            r = self.db.summary_source(fid)
            if r is None or self.db.summary(fid):
                continue
            msgs = [{"role": "system", "content": system},
                    {"role": "user", "content": f"Document: {r['name']}\n\n{(r['body'] or '')[:limit]}"}]
            try:
                kw = {"deep": False}
                if model:
                    kw["model"] = model
                    kw["keep_alive"] = "15m"
                kw["max_tokens"] = 180 if short else 400
                try:
                    s_ = self.ai.chat(msgs, **kw)
                except TypeError:      # older / fake AI without these options
                    s_ = self.ai.chat(msgs, deep=False)
            except Exception as e:
                self.log(f"Night analysis paused: {e}")
                return done
            self.db.save_summary(fid, (s_ or "").strip()[:1500], model or self.ai.chat_model_label())
            done += 1
            if not gpu_logged and hasattr(self.ai, "gpu_status") and not self.ai.online:
                self.log("Model runs on: " + self.ai.gpu_status())
                gpu_logged = True
            rate = (time.time() - t0) / done
            left = len(plan) - done
            self.progress(done0 + done, total, f"summarising · {rate:.0f} s/doc · about {left * rate / 3600:.1f} h left")
        self.log(f"Night analysis: {done} document(s) summarised.")
        return done

    def classify_existing(self) -> int:
        """Gives a drawing type to files indexed by older versions, from the stored text (files are not re-read)."""
        done = 0
        while not self.should_stop():
            rows = self.db.untyped(2000)
            if not rows:
                break
            items = [(doctype.classify(r["name"], r["ext"], r["kind"], r["body"] or "",
                                       r["kind"] == "drawing"), r["id"]) for r in rows]
            self.db.set_dtypes(items)
            done += len(items)
            self.progress(done, done + len(self.db.untyped(1)), "drawing types")
        if done:
            c = self.db.dtype_counts()
            self.log(f"Drawing types recognised for {done} files: " + ", ".join(
                f"{doctype.LABELS.get(k, k)} {v}" for k, v in sorted(c.items(), key=lambda x: -x[1]) if k))
        return done

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
            self._wait_if_paused()
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
