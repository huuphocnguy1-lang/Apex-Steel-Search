"""Main window, background indexing thread and folder watcher."""
import logging
import os
import queue
import sys
import time
import traceback

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..ai import AIClient
from ..config import Config, data_dir
from ..db import DB
from ..indexer import Indexer
from .common import STYLE, PreviewDialog, Runner, resource_path
from .analyse import CasesPage, HydraulicsPage, IbaPage, SpecialistPage
from .pages import (AssistantPage, DuplicatesPage, FoldersPage, LibraryPage, PhotosPage, RevisionsPage,
                    SearchPage, SettingsPage)

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ background indexing
class IndexWorker(QThread):
    progress = Signal(int, int, str)
    message = Signal(str)
    changed = Signal()
    busy = Signal(bool)

    def __init__(self, cfg, db, ai):
        super().__init__()
        self.cfg, self.db, self.ai = cfg, db, ai
        self.jobs = queue.Queue()
        self.pending = {}            # path -> time of last change (debounce for the watcher)
        self._stop = False
        self._cancel = False
        self.is_busy = False
        self.hold = False          # True while you are asking the AI: background AI work waits
        self.night_idle = False    # True during automatic night analysis: wait while the laptop is used
        self.indexer = Indexer(db, cfg, ai, log_fn=self.message.emit, progress=self.progress.emit,
                               should_stop=lambda: self._stop or self._cancel, paused=self._paused)

    def _paused(self):
        if self.hold:
            return True
        return self.night_idle and user_idle_seconds() < 180

    def enqueue(self, job):
        self.jobs.put(job)

    def file_event(self, path):
        self.jobs.put(("path", path))

    def cancel(self):
        self._cancel = True
        self.message.emit("Stopping…")

    def stop(self):
        self._stop = True
        self.jobs.put(("noop",))

    def run(self):
        while not self._stop:
            try:
                job = self.jobs.get(timeout=1.0)
            except queue.Empty:
                job = None
            if job and job[0] == "path":
                self.pending[job[1]] = time.time()
                continue
            self._flush_pending()
            if job is None or job[0] == "noop":
                continue
            self._cancel = False
            self.is_busy = True
            self.busy.emit(True)
            try:
                if job[0] == "scan":
                    self.indexer.scan()
                    self.changed.emit()
                    if self.cfg.get("auto_smart") and not self._cancel:
                        self.indexer.embed_pending(quiet=True)
                elif job[0] == "embed":
                    self.indexer.embed_pending()
                elif job[0] == "classify":
                    self.indexer.classify_existing()
                elif job[0] == "night":
                    auto = len(job) > 1 and job[1]
                    self.night_idle = bool(auto and self.cfg.get("night_only_idle", True))
                    try:
                        self.message.emit("🌙 Night analysis started")
                        self.indexer.scan()
                        self.changed.emit()
                        self.indexer.embed_pending(quiet=True)
                        self.indexer.summarize_pending(self.cfg.get("night_folders", []))
                        self.indexer.embed_pending(quiet=True)
                        self.message.emit("🌙 Night analysis finished")
                    finally:
                        self.night_idle = False
            except Exception as e:
                log.exception("indexing job failed")
                self.message.emit(f"✘ Error: {e}")
            self.is_busy = False
            self.busy.emit(False)
            self.changed.emit()

    def _flush_pending(self):
        now = time.time()
        ready = [p for p, t in self.pending.items() if now - t > 2.0]
        if not ready:
            return
        for p in ready:
            self.pending.pop(p, None)
            try:
                if os.path.isfile(p):
                    self.indexer.index_path(p)
                else:
                    self.indexer.remove_path(p)
            except Exception as e:
                self.message.emit(f"✘ {os.path.basename(p)}: {e}")
        self.changed.emit()


def user_idle_seconds() -> float:
    """Seconds since the last keyboard/mouse input (Windows). Elsewhere: always 'idle'."""
    if sys.platform != "win32":
        return 1e9
    try:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        li = LASTINPUTINFO()
        li.cbSize = ctypes.sizeof(li)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
            return 1e9
        return (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0
    except Exception:
        return 1e9


class FolderWatcher:
    """Watches folders with watchdog and forwards changes to the worker."""

    def __init__(self, callback):
        self.callback = callback
        self.observer = None

    def start(self, folders):
        self.stop()
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            log.warning("watchdog not installed: automatic updates disabled")
            return
        cb = self.callback

        class H(FileSystemEventHandler):
            def on_any_event(self, e):
                if e.is_directory:
                    return
                for p in (getattr(e, "src_path", None), getattr(e, "dest_path", None)):
                    if p:
                        cb(os.fsdecode(p))

        self.observer = Observer()
        for f in folders:
            try:
                self.observer.schedule(H(), f, recursive=True)
            except Exception as e:
                log.warning("cannot watch %s: %s", f, e)
        self.observer.daemon = True
        self.observer.start()

    def stop(self):
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=2)
            except Exception:
                pass
            self.observer = None


# ------------------------------------------------------------------ main window
class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, db: DB, selftest=False):
        super().__init__()
        self.cfg, self.db, self.selftest = cfg, db, selftest
        self.ai = AIClient(cfg)
        self.runner = Runner()
        self.worker = IndexWorker(cfg, db, self.ai)
        self.watcher = FolderWatcher(self.worker.file_event)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource_path("assets", "icon.ico")))
        self.resize(1360, 860)

        central = QWidget()
        central.setObjectName("central")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._header())
        body = QHBoxLayout()
        body.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(215)
        self.stack = QStackedWidget()
        self.pages = {}
        for key, label, page in [
            ("search", "🔎   Keyword search", SearchPage(self, smart=False)),
            ("smart", "🧠   Smart search", SearchPage(self, smart=True)),
            ("assistant", "💬   AI assistant", AssistantPage(self)),
            ("specialist", "🛠   Steel Specialist", SpecialistPage(self)),
            ("iba", "📈   iba Analyzer", IbaPage(self)),
            ("hydraulics", "🔧   Hydraulics", HydraulicsPage(self)),
            ("cases", "📒   Lessons learned", CasesPage(self)),
            ("library", "🏷   Library & tags", LibraryPage(self)),
            ("revisions", "📐   Revisions", RevisionsPage(self)),
            ("photos", "🖼   Photos & OCR", PhotosPage(self)),
            ("duplicates", "🧬   Duplicates", DuplicatesPage(self)),
            ("folders", "📁   Folders & index", FoldersPage(self)),
            ("settings", "⚙   Settings", SettingsPage(self)),
        ]:
            self.pages[key] = page
            self.stack.addWidget(page)
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, key)
            self.nav.addItem(it)
        self.nav.currentRowChanged.connect(self._on_nav)
        body.addWidget(self.nav)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        self.setCentralWidget(central)

        self.bar = QProgressBar()
        self.bar.setMaximumWidth(220)
        self.bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.bar)
        self.status_lbl = QLabel()
        self.statusBar().addPermanentWidget(self.status_lbl)

        folders_page = self.pages["folders"]
        self.worker.message.connect(folders_page.append_log)
        self.worker.message.connect(self._on_message)
        self.worker.progress.connect(folders_page.set_progress)
        self.worker.progress.connect(self._on_progress)
        self.worker.changed.connect(self._on_changed)
        self.worker.busy.connect(self._on_busy)
        self._change_timer = QTimer(self)
        self._change_timer.setSingleShot(True)
        self._change_timer.timeout.connect(self._refresh_pages)

        self.mode_changed()
        self.worker.start()
        self._night_timer = QTimer(self)
        self._night_timer.timeout.connect(self._night_check)
        self._night_timer.start(60_000)
        if not selftest and not cfg.get("mode") == "online":
            self.runner.run(self.ai.warm_up, ())   # load the local model now → first question is fast
        self.worker.enqueue(("classify",))
        if not selftest:
            self.watcher.start(cfg.enabled_folders())
            self.worker.enqueue(("scan",))
        self.nav.setCurrentRow(0 if cfg.get("folders") else list(self.pages).index("folders"))
        if not cfg.get("folders") and not selftest:
            QTimer.singleShot(400, self._welcome)

    def _header(self):
        h = QWidget()
        h.setObjectName("header")
        h.setFixedHeight(60)
        lay = QHBoxLayout(h)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(QPixmap(resource_path("assets", "icon.png")).scaled(
            38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        title = QLabel(f"{APP_NAME}")
        title.setObjectName("appTitle")
        self.gsearch = QLineEdit()
        self.gsearch.setObjectName("globalSearch")
        self.gsearch.setPlaceholderText("🔎  Search drawings, PDF, Word, Excel, photos…   (Enter)")
        self.gsearch.setMaximumWidth(640)
        self.gsearch.returnPressed.connect(self._global_search)
        grp = QButtonGroup(self)
        self.m_off = QPushButton("🔒 Offline")
        self.m_on = QPushButton("☁ Online")
        for b in (self.m_off, self.m_on):
            b.setObjectName("modeBtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            grp.addButton(b)
        grp.setExclusive(True)
        self.m_off.clicked.connect(lambda: self._set_mode("offline"))
        self.m_on.clicked.connect(lambda: self._set_mode("online"))
        self.hstat = QLabel()
        self.hstat.setStyleSheet("font-size:9pt")
        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addSpacing(10)
        lay.addWidget(self.gsearch, 1)
        lay.addWidget(self.m_off)
        lay.addWidget(self.m_on)
        lay.addWidget(self.hstat)
        return h

    # ------------------------------------------------------------ context API used by pages
    def show_file(self, fid):
        dlg = PreviewDialog(self, fid, self)
        dlg.exec()

    def ask_ai(self, question):
        self.go("assistant")
        self.pages["assistant"].ask(question)

    def go(self, key):
        keys = list(self.pages)
        self.nav.setCurrentRow(keys.index(key))

    def set_status(self, msg):
        self.statusBar().showMessage(msg, 6000)

    def folders_changed(self):
        self.watcher.start(self.cfg.enabled_folders())
        self.worker.enqueue(("scan",))

    def mode_changed(self):
        on = self.cfg.get("mode") == "online"
        self.m_on.setChecked(on)
        self.m_off.setChecked(not on)
        self.hstat.setText("☁ cloud AI" if on else "🔒 data stays on this laptop")
        self.status_lbl.setText(f"v{__version__} · {'Online' if on else 'Offline'}")
        self.pages["assistant"].dirty = True

    # ------------------------------------------------------------ internals
    def _set_mode(self, mode):
        self.cfg["mode"] = mode
        self.cfg.save()
        self.mode_changed()
        self.set_status("Online: the assistant uses the cloud AI" if mode == "online"
                        else "Offline: everything runs on this laptop")
        if self.stack.currentWidget() is self.pages["assistant"]:
            self.pages["assistant"].refresh()

    def _global_search(self):
        t = self.gsearch.text().strip()
        if not t:
            return
        cur = self.stack.currentWidget()
        if cur is self.pages["smart"]:
            self.pages["smart"].search_text(t)
        elif cur is self.pages["assistant"]:
            self.pages["assistant"].ask(t)
            self.gsearch.clear()
        else:
            self.go("search")
            self.pages["search"].search_text(t)

    def _on_nav(self, row):
        key = self.nav.item(row).data(Qt.ItemDataRole.UserRole)
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        page.on_show()

    def _night_check(self):
        import datetime
        c = self.cfg
        if not c.get("night_auto") or not c.get("night_folders"):
            return
        try:
            hh, mm = (int(x) for x in str(c.get("night_start", "22:00")).split(":")[:2])
        except ValueError:
            hh, mm = 22, 0
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        if (now.hour, now.minute) >= (hh, mm) and c.get("night_last") != today:
            c["night_last"] = today
            c.save()
            self.worker.enqueue(("night", True))

    def _on_changed(self):
        self._change_timer.start(1500)

    def _refresh_pages(self):
        for p in self.pages.values():
            p.dirty = True
        cur = self.stack.currentWidget()
        if cur in (self.pages["folders"], self.pages["library"], self.pages["duplicates"]):
            cur.on_show()

    def _on_busy(self, busy):
        self.bar.setVisible(busy)
        fp = self.pages["folders"]
        if busy:
            fp.state.setText("Working…")
            fp.state.setStyleSheet("")
        else:
            fp.set_progress(1, 1, "")
            self.statusBar().showMessage("✔ Finished — index up to date", 8000)

    def _on_progress(self, i, n, name):
        self.bar.setValue(int(i * 100 / n) if n else 100)

    def _on_message(self, msg):
        if not msg.startswith(("✓", "−")):
            self.statusBar().showMessage(msg, 8000)

    def _welcome(self):
        QMessageBox.information(self, f"Welcome to {APP_NAME}",
                                "Start by adding the folders that contain your drawings, documents and photos.\n\n"
                                "Click “＋ Add folder”. The first indexing runs in the background — "
                                "you can search while it works.")

    def closeEvent(self, e):
        self.watcher.stop()
        self.worker.stop()
        self.worker.wait(5000)
        super().closeEvent(e)


# ------------------------------------------------------------------ entry
def run_app(selftest=False) -> int:
    logging.basicConfig(filename=str(data_dir() / "app.log"), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", encoding="utf-8")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    def excepthook(t, v, tb):
        logging.error("Unhandled: %s", "".join(traceback.format_exception(t, v, tb)))
        if not selftest:
            QMessageBox.critical(None, APP_NAME, f"Unexpected error:\n{v}\n\nDetails in {data_dir() / 'app.log'}")
    sys.excepthook = excepthook

    cfg = Config()
    db = DB(data_dir() / "index.db")
    w = MainWindow(cfg, db, selftest=selftest)
    w.show()
    if selftest:
        def check():
            for i in range(w.nav.count()):
                w.nav.setCurrentRow(i)
                app.processEvents()
            w.pages["search"].search_text("anchor bolt")
            app.processEvents()
            print("SELFTEST OK", __version__)
            w.close()
            app.quit()
        QTimer.singleShot(800, check)
    code = app.exec()
    db.close()
    return code
