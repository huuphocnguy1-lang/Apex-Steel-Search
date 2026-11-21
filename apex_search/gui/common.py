"""Shared GUI helpers: style, background tasks, thumbnails, preview panel."""
import datetime
import html
import logging
import os
import re
import subprocess
import sys

from PySide6.QtCore import QObject, QRect, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QFont, QImage, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTextBrowser,
                               QVBoxLayout, QWidget)

from ..extract import IMAGE_EXTS
from ..search import highlight_html

log = logging.getLogger(__name__)

STEEL, STEEL2, AMBER, BG = "#1F4E79", "#2C6AA0", "#F2A900", "#F4F6F9"

STYLE = f"""
QWidget {{ font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif; font-size: 10pt; color: #1B2430; }}
QMainWindow, #central, #page {{ background: {BG}; }}
#header {{ background: {STEEL}; }}
#header QLabel {{ color: white; }}
#appTitle {{ font-size: 13pt; font-weight: 600; }}
#globalSearch {{ background: white; border: 0; border-radius: 8px; padding: 7px 10px; font-size: 10.5pt; }}
#modeBtn {{ background: rgba(255,255,255,0.15); color: white; border: 0; border-radius: 7px; padding: 6px 14px; font-weight: 600; }}
#modeBtn:checked {{ background: white; color: {STEEL}; }}
#nav {{ background: white; border: 0; border-right: 1px solid #E1E6ED; padding: 8px; outline: 0; font-size: 10.5pt; }}
#nav::item {{ padding: 9px 10px; border-radius: 8px; margin: 1px 0; }}
#nav::item:selected {{ background: #E8F0F8; color: {STEEL}; font-weight: 600; }}
#nav::item:hover:!selected {{ background: {BG}; }}
QLabel#h1 {{ font-size: 16pt; font-weight: 700; }}
QLabel#sub {{ color: #5F6D7E; }}
QLabel#card, QFrame#card {{ background: white; border: 1px solid #E1E6ED; border-radius: 10px; padding: 10px; }}
QPushButton {{ background: {STEEL}; color: white; border: 0; border-radius: 7px; padding: 7px 14px; font-weight: 600; }}
QPushButton:hover {{ background: {STEEL2}; }}
QPushButton:disabled {{ background: #A9BACB; }}
QPushButton[ghost="true"] {{ background: white; color: {STEEL}; border: 1px solid #D5DCE5; }}
QPushButton[ghost="true"]:hover {{ border-color: {STEEL2}; }}
QPushButton[amber="true"] {{ background: {AMBER}; color: #2B2000; }}
QPushButton[chip="true"] {{ background: #FFF4D6; color: #6B4C00; border: 1px solid #F3D98A; border-radius: 12px; padding: 4px 12px; font-weight: 500; }}
QLineEdit, QComboBox, QSpinBox {{ background: white; border: 1px solid #D5DCE5; border-radius: 7px; padding: 6px 8px; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {STEEL2}; }}
QListWidget, QTableWidget, QTreeWidget, QTextBrowser, QPlainTextEdit {{ background: white; border: 1px solid #E1E6ED; border-radius: 8px; }}
QListWidget#results::item {{ border-bottom: 1px solid #EEF1F5; }}
QListWidget#results::item:selected {{ background: #E8F0F8; }}
QHeaderView::section {{ background: #FAFBFC; border: 0; border-bottom: 1px solid #E1E6ED; padding: 6px; font-weight: 600; color: #5F6D7E; }}
QTableWidget {{ gridline-color: #EEF1F5; selection-background-color: #E8F0F8; selection-color: #1B2430; }}
QProgressBar {{ border: 0; background: #E7ECF2; border-radius: 5px; height: 12px; text-align: center; font-size: 8pt; }}
QProgressBar::chunk {{ background: {STEEL2}; border-radius: 5px; }}
QStatusBar {{ background: white; border-top: 1px solid #E1E6ED; }}
QSplitter::handle {{ background: {BG}; }}
"""

BADGE_COLORS = {"pdf": ("#FDE6E3", "#B23121"), "docx": ("#E2ECFB", "#1F57B8"), "doc": ("#E2ECFB", "#1F57B8"),
                "xlsx": ("#E1F4E8", "#1A7A45"), "xls": ("#E1F4E8", "#1A7A45"), "csv": ("#E1F4E8", "#1A7A45"),
                "dwg": ("#EDE6FA", "#5B35A8"), "dxf": ("#EDE6FA", "#5B35A8"), "msg": ("#E6F4F6", "#156B78"),
                "eml": ("#E6F4F6", "#156B78"), "pptx": ("#FDEBDD", "#B5520F")}


def badge_html(ext: str) -> str:
    bg, fg = BADGE_COLORS.get(ext, ("#FFF0D9", "#9A5B00") if ext in IMAGE_EXTS else ("#EEF0F3", "#44505E"))
    return f'<span style="background:{bg};color:{fg};font-weight:700;font-size:8pt">&nbsp;{html.escape(ext.upper())}&nbsp;</span>'


def rev_html(latest, rev) -> str:
    if latest is None or not rev:
        return ""
    if latest:
        return f'&nbsp;<span style="background:#E3F4EC;color:#1E8E5A;font-weight:700;font-size:8pt">&nbsp;✓ Latest Rev {html.escape(rev)}&nbsp;</span>'
    return f'&nbsp;<span style="background:#EEF0F3;color:#5F6D7E;font-weight:700;font-size:8pt">&nbsp;Superseded Rev {html.escape(rev)}&nbsp;</span>'


def fmt_date(ts) -> str:
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def fmt_size(n) -> str:
    n = n or 0
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return ""


def h1(text):
    lb = QLabel(text)
    lb.setObjectName("h1")
    return lb


def sub(text):
    lb = QLabel(text)
    lb.setObjectName("sub")
    lb.setWordWrap(True)
    return lb


def button(text, ghost=False, amber=False, chip=False, tip=None):
    b = QPushButton(text)
    if ghost:
        b.setProperty("ghost", True)
    if amber:
        b.setProperty("amber", True)
    if chip:
        b.setProperty("chip", True)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def resource_path(*parts) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    return os.path.join(base, *parts)


def open_file(path: str):
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError as e:
        log.warning("open failed: %s", e)


def open_folder(path: str):
    try:
        if sys.platform == "win32":
            subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
        else:
            open_file(os.path.dirname(path))
    except OSError as e:
        log.warning("open folder failed: %s", e)


def md_to_html(text: str) -> str:
    """Tiny markdown → HTML for AI answers. [n] citations become links src:n."""
    out, in_list = [], False
    for line in (text or "").splitlines():
        s = html.escape(line.rstrip())
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        m = re.match(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)", s)
        if m:
            if not in_list:
                out.append("<ul style='margin:2px 0'>")
                in_list = True
            out.append(f"<li>{m.group(1)}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if re.match(r"^#{1,4}\s", s):
            s = "<b>" + s.lstrip("#").strip() + "</b>"
        out.append(s + "<br>" if s else "<br>")
    if in_list:
        out.append("</ul>")
    h = "".join(out)
    return re.sub(r"\[(\d{1,2})\]", r'<a href="cite:\1" style="color:#1F4E79;font-weight:700;text-decoration:none">[\1]</a>', h)


# ------------------------------------------------------------------ background tasks
class _Signals(QObject):
    done = Signal(object)
    error = Signal(str)


class _Task(QRunnable):
    def __init__(self, fn, args):
        super().__init__()
        self.fn, self.args, self.signals, self.finished = fn, args, _Signals(), False
        self.setAutoDelete(False)

    def run(self):
        try:
            r = self.fn(*self.args)
        except Exception as e:
            log.exception("background task failed")
            self.signals.error.emit(f"{type(e).__name__}: {e}" if str(e) else type(e).__name__)
        else:
            self.signals.done.emit(r)
        self.finished = True


class TokenStream(QObject):
    """Created in the GUI thread; its emit() may be called from a worker thread (queued to the GUI)."""
    token = Signal(str)


def hold_background(ctx, on: bool):
    w = getattr(ctx, "worker", None)
    if w is not None:
        w.hold = on


class Runner:
    """Runs a function in a worker thread; callbacks must be methods of QWidgets (run in the GUI thread)."""

    def __init__(self):
        self.pool = QThreadPool.globalInstance()
        self.tasks = []

    def run(self, fn, args=(), on_done=None, on_error=None):
        self.tasks = [t for t in self.tasks if not t.finished]
        t = _Task(fn, tuple(args))
        if on_done is not None:
            t.signals.done.connect(on_done)
        if on_error is not None:
            t.signals.error.connect(on_error)
        self.tasks.append(t)
        self.pool.start(t)
        return t


# ------------------------------------------------------------------ thumbnails
_THUMBS: dict = {}


def placeholder(ext: str, size: QSize) -> QPixmap:
    pm = QPixmap(size)
    pm.fill(QColor("white"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg, fg = BADGE_COLORS.get(ext, ("#EEF0F3", "#44505E"))
    p.setPen(QColor("#E1E6ED"))
    p.drawRect(0, 0, size.width() - 1, size.height() - 1)
    w, h = min(120, size.width() // 2), min(48, size.height() // 3)
    p.setBrush(QColor(bg))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect((size.width() - w) // 2, (size.height() - h) // 2, w, h, 8, 8)
    p.setPen(QColor(fg))
    f = QFont()
    f.setBold(True)
    f.setPointSize(max(8, h // 3))
    p.setFont(f)
    p.drawText(QRect((size.width() - w) // 2, (size.height() - h) // 2, w, h), Qt.AlignmentFlag.AlignCenter, ext.upper())
    p.end()
    return pm


def load_thumb_image(path: str, ext: str, w: int, h: int):
    """Returns a QImage (safe to call from worker threads) or None."""
    try:
        if ext in IMAGE_EXTS:
            r = QImageReader(path)
            r.setAutoTransform(True)
            s = r.size()
            if s.isValid():
                r.setScaledSize(s.scaled(QSize(w, h), Qt.AspectRatioMode.KeepAspectRatio))
            img = r.read()
            return None if img.isNull() else img
        if ext == "pdf":
            import fitz
            with fitz.open(path) as d:
                if d.page_count == 0:
                    return None
                page = d[0]
                z = min(w / page.rect.width, h / page.rect.height) * 1.5
                pix = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                return img.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    except Exception as e:
        log.debug("thumb failed %s: %s", path, e)
    return None


def thumb_pixmap(path: str, ext: str, w: int = 420, h: int = 280) -> QPixmap:
    key = (path, w, h)
    if key in _THUMBS:
        return _THUMBS[key]
    img = load_thumb_image(path, ext, w, h)
    pm = QPixmap.fromImage(img) if img is not None else placeholder(ext, QSize(w, h))
    if len(_THUMBS) > 400:
        _THUMBS.clear()
    _THUMBS[key] = pm
    return pm


# ------------------------------------------------------------------ preview panel
class PreviewWidget(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx, self.fid, self.path = ctx, None, None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setMinimumHeight(180)
        self.thumb.setStyleSheet("background:white;border:1px solid #E1E6ED;border-radius:8px")
        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size:12pt;font-weight:700")
        self.meta = QLabel()
        self.meta.setWordWrap(True)
        self.meta.setTextFormat(Qt.TextFormat.RichText)
        self.meta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.meta.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.text = QTextBrowser()
        row = QHBoxLayout()
        self.b_open = button("Open file")
        self.b_folder = button("Open folder", ghost=True)
        self.b_ask = button("💬 Ask AI about it", ghost=True)
        for b in (self.b_open, self.b_folder, self.b_ask):
            row.addWidget(b)
        row.addStretch()
        self.b_open.clicked.connect(self.on_open)
        self.b_folder.clicked.connect(self.on_folder)
        self.b_ask.clicked.connect(self.on_ask)
        v.addWidget(self.thumb)
        v.addWidget(self.title)
        v.addWidget(self.meta)
        v.addWidget(self.text, 1)
        v.addLayout(row)
        self.clear()

    def clear(self):
        self.fid = self.path = None
        self.thumb.setPixmap(QPixmap())
        self.thumb.setText("Select a result to preview it")
        self.title.setText("")
        self.meta.setText("")
        self.text.setHtml("")
        for b in (self.b_open, self.b_folder, self.b_ask):
            b.setEnabled(False)

    def set_file(self, fid: int, terms=()):
        r = self.ctx.db.get(fid)
        if r is None:
            self.clear()
            return
        self.fid, self.path = fid, r["path"]
        self.thumb.setPixmap(thumb_pixmap(r["path"], r["ext"]))
        self.title.setText(r["title"] or r["name"])
        latest = self.ctx.db.latest_revs().get(r["dno"]) == r["rev"] if r["dno"] else None
        rows = [("File", html.escape(r["name"])), ("Folder", html.escape(os.path.dirname(r["path"]))),
                ("Project", html.escape(r["project"] or "—")),
                ("Date · size", f"{fmt_date(r['mtime'])} · {fmt_size(r['size'])}")]
        if r["dno"]:
            rows.append(("Drawing", f"{html.escape(r['dno'])} {rev_html(latest, r['rev'])}"))
        if r["material"]:
            rows.append(("Material", html.escape(r["material"])))
        rows.append(("Language", html.escape(r["lang"] or "—") + (" · text read by OCR" if r["ocr"] else "")))
        if r["error"]:
            rows.append(("Note", f'<span style="color:#9A5B00">{html.escape(r["error"])}</span>'))
        self.meta.setText(f"{badge_html(r['ext'])}<table cellspacing=3>" + "".join(
            f'<tr><td style="color:#5F6D7E;padding-right:10px">{k}</td><td>{v}</td></tr>' for k, v in rows) + "</table>")
        body = self.ctx.db.body(fid)
        self.text.setHtml('<div style="white-space:pre-wrap;font-size:9.5pt">' +
                          (highlight_html(body[:80000], terms) if body else "<i>No text in this file.</i>") + "</div>")
        for b in (self.b_open, self.b_folder, self.b_ask):
            b.setEnabled(True)

    def on_open(self):
        if self.path:
            open_file(self.path)

    def on_folder(self):
        if self.path:
            open_folder(self.path)

    def on_ask(self):
        if self.fid:
            r = self.ctx.db.get(self.fid)
            self.ctx.ask_ai(f"Summarise the key technical points of {r['name']}.")


class PreviewDialog(QDialog):
    def __init__(self, ctx, fid, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Document preview")
        self.resize(640, 760)
        v = QVBoxLayout(self)
        self.p = PreviewWidget(ctx, self)
        v.addWidget(self.p)
        self.p.set_file(fid)
        self.p.b_ask.clicked.connect(self.accept)
