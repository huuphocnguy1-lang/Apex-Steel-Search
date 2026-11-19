"""Analyse pages: Steel Specialist, iba Analyzer, Hydraulics, Lessons learned."""
import datetime
import html
import os

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QGraphicsPixmapItem,
                               QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter, QTableWidget,
                               QTableWidgetItem, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from .. import hydraulics, iba, specialist
from .common import button, h1, md_to_html, sub
from .pages import AssistantPage, Page, export_rows_xlsx

AREA_NAMES = dict(specialist.AREAS)


# ================================================================== lessons learned dialog
class CaseDialog(QDialog):
    def __init__(self, parent, case=None, area="Caster", symptom=""):
        super().__init__(parent)
        self.setWindowTitle("Lesson learned")
        self.resize(560, 420)
        c = dict(case) if case else {}
        f = QFormLayout(self)
        self.date = QLineEdit(c.get("date") or datetime.date.today().isoformat())
        self.area = QComboBox()
        for k, l in specialist.AREAS:
            self.area.addItem(l, k)
        self.area.addItem("Other", "Other")
        self.area.setCurrentIndex(max(0, self.area.findData(c.get("area") or area)))
        self.symptom = QPlainTextEdit(c.get("symptom") or symptom)
        self.cause = QPlainTextEdit(c.get("cause") or "")
        self.fix = QPlainTextEdit(c.get("fix") or "")
        self.author = QLineEdit(c.get("author") or "")
        for w in (self.symptom, self.cause, self.fix):
            w.setFixedHeight(70)
        f.addRow("Date", self.date)
        f.addRow("Area", self.area)
        f.addRow("Symptom", self.symptom)
        f.addRow("Root cause", self.cause)
        f.addRow("Fix / action", self.fix)
        f.addRow("By", self.author)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self.cid = c.get("id")

    def data(self):
        return {"id": self.cid, "date": self.date.text().strip(), "area": self.area.currentData(),
                "symptom": self.symptom.toPlainText().strip(), "cause": self.cause.toPlainText().strip(),
                "fix": self.fix.toPlainText().strip(), "author": self.author.text().strip()}


def edit_case(parent, db, case=None, area="Caster", symptom="") -> bool:
    dlg = CaseDialog(parent, case, area, symptom)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        d = dlg.data()
        if not d["symptom"]:
            QMessageBox.information(parent, "Lesson learned", "Write the symptom first.")
            return False
        db.case_save(d)
        return True
    return False


# ================================================================== casting temperature dialog
class TempDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Casting temperatures")
        f = QFormLayout(self)
        self.comp = {}
        defaults = {"C": 0.05, "Si": 0.02, "Mn": 0.25, "P": 0.012, "S": 0.008, "Al": 0.035, "Cu": 0.03, "Ni": 0.03, "Cr": 0.03}
        for k, val in defaults.items():
            sp = QDoubleSpinBox()
            sp.setDecimals(3)
            sp.setRange(0, 5)
            sp.setSingleStep(0.01)
            sp.setValue(val)
            sp.valueChanged.connect(self.update_temp)
            self.comp[k] = sp
            f.addRow(f"% {k}", sp)
        self.sh = QDoubleSpinBox()
        self.sh.setRange(0, 80)
        self.sh.setValue(25)
        self.loss = QDoubleSpinBox()
        self.loss.setRange(0, 120)
        self.loss.setValue(38)
        self.sh.valueChanged.connect(self.update_temp)
        self.loss.valueChanged.connect(self.update_temp)
        f.addRow("Superheat °C", self.sh)
        f.addRow("Ladle losses °C", self.loss)
        self.out = QLabel()
        f.addRow(self.out)
        f.addRow(sub("General empirical formula — your plant grade table always has priority."))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self.update_temp()

    def update_temp(self, *_):
        t = specialist.casting_temperatures({k: s.value() for k, s in self.comp.items()}, self.sh.value(), self.loss.value())
        self.out.setText(f"Liquidus <b>{t['liquidus']:.0f} °C</b> · Tundish target <b style='color:#1F4E79'>"
                         f"{t['tundish']:.0f} °C</b> · Ladle arrival ≈ <b>{t['ladle']:.0f} °C</b>")


# ================================================================== Steel Specialist
class SpecialistPage(AssistantPage):
    TITLE = "Steel Specialist"
    SUBTITLE = ("Troubleshooting for ESP, casting, hot strip mill, pay-off reel, laminar cooling and hydraulics — from "
                "your documents, your lessons learned and your photos (📎 / drag & drop / 📋 paste screenshot).")
    BOT = "Steel Specialist"
    INTRO = ("Choose the area, describe the symptom (what, where, when, alarms, values) and add a photo if you have one. "
             "Answers follow: what I see → likely causes → checks → actions → safety.")
    SUGGEST = ["Mould level hunting", "Strip break F5–F6", "Coiling temp too high", "Servo valve hunting"]

    def __init__(self, ctx):
        self.area = "Caster"
        self._extra = ""
        self._last_q = ""
        super().__init__(ctx)
        bar = QHBoxLayout()
        self.area_group = QButtonGroup(self)
        self.area_group.setExclusive(True)
        for k, l in specialist.AREAS:
            b = QPushButton(l)
            b.setCheckable(True)
            b.setProperty("chip", True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("QPushButton:checked{background:#1F4E79;color:white;border-color:#1F4E79}")
            b.clicked.connect(lambda _=False, key=k: self.set_area(key))
            self.area_group.addButton(b)
            bar.addWidget(b)
            if k == self.area:
                b.setChecked(True)
        bar.addStretch()
        self.col.insertLayout(0, bar)

    def set_area(self, key):
        self.area = key

    def build_side(self):
        side = QWidget()
        side.setFixedWidth(250)
        v = QVBoxLayout(side)
        v.setContentsMargins(0, 0, 0, 0)
        cbox = QGroupBox("📒 Lessons learned")
        cv = QVBoxLayout(cbox)
        cv.addWidget(sub("Similar past cases are used automatically in the answers."))
        b = button("＋ Save a new case", ghost=True)
        b.clicked.connect(lambda: edit_case(self, self.ctx.db, area=self.area))
        cv.addWidget(b)
        v.addWidget(cbox)
        tb = button("🌡 Casting temperatures…", ghost=True, tip="Liquidus, tundish target and ladle arrival temperature")
        tb.clicked.connect(lambda: TempDialog(self).exec())
        v.addWidget(tb)
        v.addStretch()
        return side

    def answer_call(self, q, files):
        self._last_q = q
        return specialist.specialist_with_files, (self.ctx.db, self.ctx.ai, self.area, q, list(self.history), files,
                                                  dict(self.ctx.cfg), self._extra)

    def answer_footer(self, res):
        self._extra = ""
        return ('<br><a href="case:new" style="color:#8A6100;text-decoration:none;font-size:8.5pt">'
                '📒 Save this problem as a lesson learned</a>')

    def on_link(self, url):
        if url.toString() == "case:new":
            if edit_case(self, self.ctx.db, area=self.area, symptom=self._last_q):
                self.ctx.set_status("Lesson learned saved — it will be used in future answers")
            return
        super().on_link(url)

    def ask_with_context(self, area, question, context):
        """Used by the iba Analyzer: ask the specialist with the analysis results as context."""
        self.area = area
        for b in self.area_group.buttons():
            b.setChecked(b.text() == AREA_NAMES.get(area))
        self._extra = context
        self.ask(question)


# ================================================================== iba plot widget
COLORS = ["#1F4E79", "#C47D00", "#1E8E5A", "#8E44AD", "#C0392B", "#16708A", "#555555", "#B5520F"]


class SignalPlot(QWidget):
    windowChanged = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.rec = None
        self.refs = []
        self.on, self.events, self.win = [], {}, None
        self.hx = None
        self.drag = None
        self.setMinimumHeight(320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_data(self, rec, on, events, refs=None, reset=False):
        """refs: list of (Recording, colour) drawn as overlays aligned on the start of the main recording."""
        self.rec, self.on, self.refs = rec, on, refs or []
        self.events = {e["signal"]: e for e in events}
        if reset or self.win is None:
            self.win = (float(rec.t[0]), float(rec.t[-1]))
        n = max(1, sum(on))
        self.setMinimumHeight(max(320, n * 92 + 34))
        self.update()

    def lanes(self):
        return [(k, s) for k, s in enumerate(self.rec.signals) if self.on[k]] if self.rec else []

    def _x(self, t):
        w0, w1 = self.win
        return 60 + (t - w0) / ((w1 - w0) or 1) * (self.width() - 72)

    def _t(self, x):
        w0, w1 = self.win
        return w0 + (x - 60) / max(1, self.width() - 72) * (w1 - w0)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("white"))
        if not self.rec:
            p.setPen(QColor("#5F6D7E"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Open a CSV/TXT exported from ibaAnalyzer (File → Export) to see the signals here.")
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        lanes = self.lanes()
        H = self.height() - 28
        lh = H / max(1, len(lanes))
        w0, w1 = self.win
        t = self.rec.t
        m = (t >= w0) & (t <= w1)
        small = QFont()
        small.setPointSize(8)
        for j, (k, s) in enumerate(lanes):
            y0 = j * lh
            col = QColor(COLORS[j % len(COLORS)])
            p.setPen(QColor("#E1E6ED"))
            p.setBrush(QColor("#FAFBFC"))
            p.drawRect(QRectF(60, y0 + 4, self.width() - 72, lh - 8))
            tt, vv = t[m], s.v[m]
            overlays = []
            for ref, rcol in self.refs:
                rs = next((r for r in ref.signals if r.name == s.name), None)
                if rs is not None and len(ref.t) > 1:
                    rt = ref.t - ref.t[0] + t[0]
                    mm = (rt >= w0) & (rt <= w1)
                    if mm.sum() > 1:
                        overlays.append((rt[mm], rs.v[mm], rcol))
            if len(vv) < 2:
                continue
            allv = np.concatenate([vv] + [o[1] for o in overlays])
            lo, hi = float(np.nanmin(allv)), float(np.nanmax(allv))
            span = (hi - lo) or 1.0
            Y = lambda val: y0 + lh - 12 - (val - lo) / span * (lh - 30)
            width = max(50, self.width() - 72)
            for ot, ov, ocol in overlays:
                td, vd = iba.decimate(ot, ov, width)
                p.setPen(QPen(QColor(ocol), 1.1))
                p.drawPolyline(QPolygonF([QPointF(self._x(a), Y(b)) for a, b in zip(td, vd)]))
            td, vd = iba.decimate(tt, vv, width)
            p.setPen(QPen(col, 1.3))
            p.drawPolyline(QPolygonF([QPointF(self._x(a), Y(b)) for a, b in zip(td, vd)]))
            p.setFont(small)
            p.setPen(col)
            p.drawText(QPointF(66, y0 + 17), f"{s.name}  [{s.unit}]")
            p.setPen(QColor("#8A96A3"))
            p.drawText(QRectF(0, y0 + 6, 56, 14), Qt.AlignmentFlag.AlignRight, f"{hi:.4g}")
            p.drawText(QRectF(0, y0 + lh - 22, 56, 14), Qt.AlignmentFlag.AlignRight, f"{lo:.4g}")
            ev = self.events.get(s.name)
            if ev and w0 <= ev["t"] <= w1:
                x = self._x(ev["t"])
                p.setPen(QPen(QColor("#C0392B"), 1.2, Qt.PenStyle.DashLine))
                p.drawLine(QPointF(x, y0 + 4), QPointF(x, y0 + lh - 4))
                p.setBrush(QColor("#C0392B"))
                p.drawEllipse(QPointF(x, y0 + 10), 4, 4)
        if self.refs:   # legend
            names = [(self.rec.name, COLORS[0])] + [(r.name, c) for r, c in self.refs]
            x = self.width() - 12
            p.setFont(small)
            for nm, c in reversed(names[:8]):
                w = p.fontMetrics().horizontalAdvance(nm) + 22
                x -= w
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(c))
                p.drawRect(QRectF(x, 9, 12, 4))
                p.setPen(QColor("#1B2430"))
                p.drawText(QPointF(x + 15, 15), nm)
        p.setPen(QColor("#5F6D7E"))
        p.setFont(small)
        for i in range(7):
            tv = w0 + (w1 - w0) * i / 6
            p.drawText(QRectF(self._x(tv) - 40, H + 6, 80, 16), Qt.AlignmentFlag.AlignCenter, f"{tv:.4g}")
        if self.drag is not None and self.hx is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(44, 106, 160, 40))
            p.drawRect(QRectF(min(self.drag, self.hx), 0, abs(self.hx - self.drag), H))
        if self.hx is not None and self.hx >= 60:
            tv = self._t(self.hx)
            i = int(np.clip(np.searchsorted(t, tv), 0, len(t) - 1))
            p.setPen(QPen(QColor("#1B2430"), 0.8))
            p.drawLine(QPointF(self.hx, 0), QPointF(self.hx, H))
            lines = [f"t = {t[i]:.4g} {self.rec.t_label}"] + [f"{s.name}: {s.v[i]:.4g} {s.unit}" for k, s in lanes[:14]]
            fm = p.fontMetrics()
            bw = max(fm.horizontalAdvance(l) for l in lines) + 14
            bh = len(lines) * (fm.height() + 1) + 8
            bx = self.hx + 12 if self.hx + 12 + bw < self.width() else self.hx - 12 - bw
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(27, 36, 48, 225))
            p.drawRoundedRect(QRectF(bx, 8, bw, bh), 6, 6)
            p.setPen(QColor("white"))
            for n, l in enumerate(lines):
                p.drawText(QPointF(bx + 7, 8 + 4 + (n + 1) * (fm.height() + 1) - 3), l)
        p.end()

    def mouseMoveEvent(self, e):
        self.hx = e.position().x()
        self.update()

    def leaveEvent(self, e):
        if self.drag is None:
            self.hx = None
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rec:
            self.drag = e.position().x()

    def mouseReleaseEvent(self, e):
        if self.drag is not None and self.rec:
            x0, x1 = sorted((self.drag, e.position().x()))
            self.drag = None
            if x1 - x0 > 8:
                a, b = self._t(max(60, x0)), self._t(x1)
                if b > a:
                    self.win = (a, b)
                    self.windowChanged.emit(a, b)
            self.update()

    def mouseDoubleClickEvent(self, e):
        if self.rec:
            self.win = (float(self.rec.t[0]), float(self.rec.t[-1]))
            self.windowChanged.emit(*self.win)
            self.update()


# ================================================================== iba page
OVERLAY_COLORS = ["#E59866", "#76D7C4", "#BB8FCE", "#F7DC6F", "#85C1E9", "#F1948A", "#ABEBC6", "#D7BDE2"]


class IbaPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("iba Analyzer"))
        self.v.addWidget(sub("Open one or several iba recordings (.dat, or CSV/TXT exports). Events are detected automatically; "
                             "the first signal that moved is marked 🥇. Drag on the plot to zoom, double-click to reset."))
        bar = QHBoxLayout()
        b1 = button("📂 Open .dat / CSV (one or several)…")
        b1.clicked.connect(self.open_files)
        b2 = button("Load normal reference…", ghost=True, tip="Overlay a recording of normal operation in grey")
        b2.clicked.connect(self.open_ref)
        b3 = button("🩺 Diagnose .dat…", ghost=True, tip="Test how ibaAnalyzer reads one .dat file and show a report")
        b3.clicked.connect(self.diagnose)
        self.area = QComboBox()
        for k, l in specialist.AREAS:
            self.area.addItem(l, k)
        self.area.setCurrentIndex(0)
        self.info = sub("No recording loaded.")
        bar.addWidget(b1)
        bar.addWidget(b2)
        bar.addWidget(b3)
        bar.addWidget(QLabel("Area:"))
        bar.addWidget(self.area)
        bar.addWidget(self.info, 1)
        self.v.addLayout(bar)
        sp = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.files_box = QWidget()
        fb = QVBoxLayout(self.files_box)
        fb.setContentsMargins(0, 0, 0, 0)
        mr = QHBoxLayout()
        mr.addWidget(QLabel("<b>Files</b>"))
        self.mode = QComboBox()
        self.mode.addItem("Compare files (overlay)", "compare")
        self.mode.addItem("Join in time order", "join")
        self.mode.currentIndexChanged.connect(self.rebuild)
        mr.addWidget(self.mode, 1)
        fb.addLayout(mr)
        self.files = QListWidget()
        self.files.setToolTip("Click a file to make it the main recording; tick files to overlay them (compare mode)")
        self.files.currentRowChanged.connect(self.rebuild)
        self.files.itemChanged.connect(self.rebuild)
        fb.addWidget(self.files, 1)
        lv.addWidget(self.files_box, 1)
        self.files_box.setVisible(False)
        lv.addWidget(QLabel("<b>Signals</b>"))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter signals…")
        self.filter.textChanged.connect(self.filter_signals)
        self.sigs = QListWidget()
        self.sigs.itemChanged.connect(self.on_sig_toggle)
        lv.addWidget(self.filter)
        lv.addWidget(self.sigs, 2)
        sp.addWidget(left)
        right = QSplitter(Qt.Orientation.Vertical)
        self.plot = SignalPlot()
        self.plot.windowChanged.connect(self.on_window)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.plot)
        right.addWidget(sc)
        bottom = QSplitter(Qt.Orientation.Horizontal)
        self.tabs = QTabWidget()
        self.ev = QTableWidget(0, 3)
        self.ev.setHorizontalHeaderLabels(["Time", "Signal", "Event"])
        self.ev.verticalHeader().setVisible(False)
        self.ev.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ev.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabs.addTab(self.ev, "⚡ Events")
        allw = QWidget()
        al = QVBoxLayout(allw)
        al.setContentsMargins(0, 0, 0, 0)
        self.b_scan = button("Scan all files", ghost=True, tip="Detect events in every loaded file")
        self.b_scan.clicked.connect(self.scan_all)
        self.scan = QTableWidget(0, 5)
        self.scan.setHorizontalHeaderLabels(["File", "Start", "Events", "First signal to move", "Event"])
        self.scan.verticalHeader().setVisible(False)
        self.scan.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.scan.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.scan.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.scan.cellDoubleClicked.connect(self.open_scanned)
        al.addWidget(self.b_scan)
        al.addWidget(self.scan, 1)
        self.tabs.addTab(allw, "📁 All files")
        bottom.addWidget(self.tabs)
        aiw = QWidget()
        av = QVBoxLayout(aiw)
        av.setContentsMargins(0, 0, 0, 0)
        ar = QHBoxLayout()
        ar.addWidget(QLabel("<b>🤖 AI explanation</b>"))
        ar.addStretch()
        self.b_ai = button("Explain")
        self.b_ai.clicked.connect(self.explain)
        self.b_spec = button("💬 Continue in Steel Specialist", ghost=True)
        self.b_spec.clicked.connect(self.to_specialist)
        ar.addWidget(self.b_ai)
        ar.addWidget(self.b_spec)
        av.addLayout(ar)
        self.ai_out = QTextBrowser()
        self.ai_out.setOpenLinks(False)
        self.ai_out.anchorClicked.connect(self.on_link)
        av.addWidget(self.ai_out, 1)
        bottom.addWidget(aiw)
        bottom.setSizes([420, 580])
        right.addWidget(bottom)
        right.setSizes([520, 240])
        sp.addWidget(right)
        sp.setSizes([280, 900])
        self.v.addWidget(sp, 1)
        self.recs, self.rec, self.ref = [], None, None
        self.on, self.events, self.window = [], [], None

    # ---------------- diagnostic
    def diagnose(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose ONE .dat file to diagnose", "", "iba .dat (*.dat)")
        if not p:
            return
        self.info.setText("Diagnosing with ibaAnalyzer… (can take up to a minute)")
        self.ctx.runner.run(iba.diagnose_dat, (p,), self.on_diag, self.on_diag)

    def on_diag(self, txt):
        self.info.setText("Diagnostic finished.")
        dlg = QDialog(self)
        dlg.setWindowTitle("ibaAnalyzer diagnostic — send a screenshot of this")
        dlg.resize(900, 600)
        v = QVBoxLayout(dlg)
        ed = QPlainTextEdit(str(txt))
        ed.setReadOnly(True)
        ed.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt")
        v.addWidget(ed)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        cp = bb.addButton("Copy", QDialogButtonBox.ButtonRole.ActionRole)
        cp.clicked.connect(lambda: (ed.selectAll(), ed.copy()))
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        dlg.exec()

    # ---------------- loading
    def on_link(self, url):
        s = url.toString()
        if s.startswith("src:") and s[4:].isdigit() and int(s[4:]):
            self.ctx.show_file(int(s[4:]))

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open iba recordings (Ctrl/Shift for several)", "",
                                                "iba recordings (*.dat *.csv *.txt);;All files (*.*)")
        if not paths:
            return
        self.info.setText(f"Loading {len(paths)} file(s)…")
        self.ctx.runner.run(iba.load_many, (paths,), self.on_loaded, self.on_load_error)

    def load(self, path):
        self.on_loaded(iba.load_many([path]))

    def on_load_error(self, msg):
        self.info.setText("Loading failed.")
        QMessageBox.warning(self, "iba", msg)

    def on_loaded(self, res):
        if res["errors"]:
            msg = "\n\n".join(f"{f}: {e}" for f, e in res["errors"][:5])
            more = f"\n\n… and {len(res['errors']) - 5} more" if len(res["errors"]) > 5 else ""
            QMessageBox.warning(self, "iba", f"{len(res['errors'])} file(s) could not be read:\n\n{msg}{more}")
        if not res["recs"]:
            self.info.setText("No recording loaded.")
            return
        self.recs = res["recs"]
        self.files.blockSignals(True)
        self.files.clear()
        for k, r in enumerate(self.recs):
            label = r.name + (f"   {r.start:%H:%M:%S}" if r.start else "")
            it = QListWidgetItem(label)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if k < 2 else Qt.CheckState.Unchecked)
            self.files.addItem(it)
        self.files.setCurrentRow(0)
        self.files.blockSignals(False)
        self.files_box.setVisible(len(self.recs) > 1)
        self.scan.setRowCount(0)
        self.window = None
        self.ai_out.setHtml("")
        self.rebuild(reset=True, new_signals=True)

    def rebuild(self, *_, reset=False, new_signals=False):
        if not self.recs:
            return
        if len(self.recs) > 1 and self.mode.currentData() == "join":
            rec = iba.join(self.recs)
        else:
            i = max(0, self.files.currentRow())
            rec = self.recs[i]
        changed = self.rec is None or [s.name for s in rec.signals] != [s.name for s in self.rec.signals]
        self.rec = rec
        if new_signals or changed or len(self.on) != len(rec.signals):
            lazy = any(not s.loaded for s in rec.signals)
            self.on = [k < (4 if lazy else 8) for k in range(len(rec.signals))]
            self.sigs.blockSignals(True)
            self.sigs.clear()
            for k, s in enumerate(rec.signals):
                it = QListWidgetItem(f"{s.name}  [{s.unit}]" if s.unit else s.name)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked if self.on[k] else Qt.CheckState.Unchecked)
                it.setData(Qt.ItemDataRole.UserRole, k)
                self.sigs.addItem(it)
            self.sigs.blockSignals(False)
            reset = True
        keys = ("ME", "HEAT", "SEQ", "SG", "FMxW", "FMxThick", "FMxTemp")
        extra = "  ·  ".join(f"{k} {rec.info[k]}" for k in keys if k in rec.info)
        self.info.setText(f"{rec.name} · {len(rec.signals)} signals · {len(rec.t):,} samples · "
                          f"{rec.t[0]:.4g} → {rec.t[-1]:.4g} {rec.t_label}"
                          + (f" · {len(self.recs)} files loaded" if len(self.recs) > 1 else "")
                          + (f"\n{extra}" if extra else ""))
        self.info.setToolTip("\n".join(f"{k}: {v}" for k, v in rec.info.items()))
        self.recompute(reset=reset)

    def overlays(self):
        refs = []
        if len(self.recs) > 1 and self.mode.currentData() == "compare":
            main = max(0, self.files.currentRow())
            n = 0
            for k in range(self.files.count()):
                if k != main and self.files.item(k).checkState() == Qt.CheckState.Checked:
                    refs.append((self.recs[k], OVERLAY_COLORS[n % len(OVERLAY_COLORS)]))
                    n += 1
        if self.ref is not None:
            refs.append((self.ref, "#B8C2CE"))
        return refs

    def open_ref(self):
        p, _ = QFileDialog.getOpenFileName(self, "Normal reference (same signals)", "",
                                           "iba recordings (*.dat *.csv *.txt);;All files (*.*)")
        if not p:
            return
        try:
            self.ref = iba.load(p)
        except Exception as e:
            QMessageBox.warning(self, "iba", f"Cannot read this file:\n{e}")
            return
        self.recompute()

    def filter_signals(self, text):
        for i in range(self.sigs.count()):
            it = self.sigs.item(i)
            it.setHidden(text.lower() not in it.text().lower())

    def on_sig_toggle(self, it):
        k = it.data(Qt.ItemDataRole.UserRole)
        self.on[k] = it.checkState() == Qt.CheckState.Checked
        if self.on[k] and self.rec and not self.rec.signals[k].loaded:
            self.ctx.set_status(f"Reading {self.rec.signals[k].name}…")
        try:
            self.recompute()
        except Exception as e:
            self.on[k] = False
            it.setCheckState(Qt.CheckState.Unchecked)
            QMessageBox.warning(self, "iba", f"Cannot read this signal:\n{e}")

    def on_window(self, a, b):
        full = self.rec and abs(a - self.rec.t[0]) < 1e-9 and abs(b - self.rec.t[-1]) < 1e-9
        self.window = None if full else (a, b)
        self.recompute()

    def selected(self):
        return {k for k, f in enumerate(self.on) if f}

    def recompute(self, reset=False):
        if not self.rec:
            return
        w = self.window
        self.events = iba.analyse(self.rec, self.selected(), *(w if w else (None, None)))
        self.plot.set_data(self.rec, self.on, self.events, self.overlays(), reset=reset)
        self.ev.setRowCount(len(self.events))
        for i, e in enumerate(self.events):
            vals = [f"{e['t']:.4g}", ("🥇 " if i == 0 else "") + e["signal"], f"{e['type']} {e['dir']}"]
            for j, val in enumerate(vals):
                self.ev.setItem(i, j, QTableWidgetItem(val))
        self.ev.resizeColumnToContents(0)

    # ---------------- all files
    def scan_all(self):
        if not self.recs:
            return
        names = [s.name for k, s in enumerate(self.rec.signals) if self.on[k]] if self.rec else None
        rows = iba.scan_files(self.recs, names)
        self.scan.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r["file"], f"{r['start']:%Y-%m-%d %H:%M:%S}" if r["start"] else "", str(r["events"]),
                    r["first"], (f"{r['type']} at {r['t']:.4g}" if r["first"] else "—")]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if r["events"] == 0:
                    it.setForeground(QBrush(QColor("#8A96A3")))
                self.scan.setItem(i, j, it)
        self.scan.resizeColumnsToContents()
        self.tabs.setCurrentIndex(1)
        bad = sum(1 for r in rows if r["events"])
        self.ctx.set_status(f"{bad} of {len(rows)} files have events in the selected signals")

    def open_scanned(self, row, col):
        if self.mode.currentData() == "join":
            self.mode.setCurrentIndex(0)
        self.files.setCurrentRow(row)
        self.tabs.setCurrentIndex(0)

    # ---------------- AI
    def context(self):
        txt = iba.events_text(self.rec, self.events, self.selected())
        if self.window:
            txt += f"\nAnalysed time window: {self.window[0]:.4g} to {self.window[1]:.4g}."
        others = [r.name for r, c in self.overlays()]
        if others:
            txt += "\nCompared with: " + ", ".join(others)
        return txt

    def explain(self):
        if not self.rec:
            return
        self.b_ai.setEnabled(False)
        self.ai_out.setHtml("<p style='color:#5F6D7E'>🤖 Reading the events and your documents…</p>")
        q = "Explain this recording: which signal moved first, the sequence of events, the most likely root cause and what to check."
        self.ctx.runner.run(specialist.specialist_answer,
                            (self.ctx.db, self.ctx.ai, self.area.currentData(), q, [], None, self.context()),
                            self.on_ai, self.on_ai_error)

    def on_ai(self, res):
        import re
        self.b_ai.setEnabled(True)
        body = md_to_html(res["text"])
        ids = {str(n): (fid or 0) for n, fid, name, path in res["sources"]}
        body = re.sub(r'href="cite:(\d+)"', lambda m: f'href="src:{ids.get(m.group(1), 0)}"', body)
        src = "".join(f"<div>[{n}] {html.escape(name)}</div>" for n, fid, name, path in res["sources"])
        self.ai_out.setHtml(body + (f"<hr><span style='font-size:8.5pt;color:#5F6D7E'><b>Sources</b>{src}</span>" if src else ""))

    def on_ai_error(self, msg):
        self.b_ai.setEnabled(True)
        ev = "".join(f"<li><b>{e['t']:.4g}</b> – {html.escape(e['signal'])}: {e['type']} {e['dir']}</li>" for e in self.events)
        self.ai_out.setHtml(f"<p style='color:#C0392B'>⚠ AI not available: {html.escape(msg)}</p>"
                            f"<p><b>Automatic analysis</b></p><ol>{ev or '<li>No event detected</li>'}</ol>"
                            + (f"<p>First signal to move: <b>{html.escape(self.events[0]['signal'])}</b> — start the "
                               f"investigation there.</p>" if self.events else ""))

    def to_specialist(self):
        if not self.rec:
            return
        sp = self.ctx.pages["specialist"]
        self.ctx.go("specialist")
        sp.ask_with_context(self.area.currentData(), f"Troubleshoot the event in iba recording {self.rec.name}.",
                            self.context())


# ================================================================== hydraulics: PDF view
class PdfView(QGraphicsView):
    zoneSelected = Signal(QRectF)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.pix = None
        self.sel = None
        self.scale_pt = 1.0
        self._band = None
        self.rubberBandChanged.connect(self._on_band)

    def set_image(self, img: QImage, scale_pt: float):
        self.scene().clear()
        self.pix = QGraphicsPixmapItem(QPixmap.fromImage(img))
        self.scene().addItem(self.pix)
        self.scene().setSceneRect(QRectF(img.rect()))
        self.scale_pt = scale_pt
        self.sel = None
        self.resetTransform()
        self.fitInView(self.pix, Qt.AspectRatioMode.KeepAspectRatio)

    def _on_band(self, rect, a, b):
        if not rect.isNull():
            self._band = QRectF(a, b).normalized()

    def mouseReleaseEvent(self, e):
        band = self._band
        super().mouseReleaseEvent(e)
        self._band = None
        if band is not None and band.width() > 6 and band.height() > 6 and self.pix is not None:
            self.mark(band)
            s = self.scale_pt
            self.zoneSelected.emit(QRectF(band.x() / s, band.y() / s, band.width() / s, band.height() / s))

    def mark(self, rect_scene: QRectF):
        if self.sel is not None:
            self.scene().removeItem(self.sel)
        self.sel = QGraphicsRectItem(rect_scene)
        self.sel.setPen(QPen(QColor("#F2A900"), 3))
        self.sel.setBrush(QBrush(QColor(242, 169, 0, 40)))
        self.scene().addItem(self.sel)

    def wheelEvent(self, e):
        f = 1.2 if e.angleDelta().y() > 0 else 1 / 1.2
        self.scale(f, f)


# ================================================================== hydraulics page
class HydraulicsPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Hydraulics"))
        self.v.addWidget(sub("Open a hydraulic schematic (PDF). Drag a box around a zone to get an explanation: components, "
                             "function, oil flow, faults to check. Mouse wheel = zoom."))
        tabs = QTabWidget()
        tabs.addTab(self._schematic_tab(), "📄 Schematic")
        tabs.addTab(self._calc_tab(), "🧮 Calculators")
        self.v.addWidget(tabs, 1)
        self.pdf = None
        self.page_no = 0
        self.zone = None

    # ---------------- schematic
    def _schematic_tab(self):
        w = QWidget()
        h = QHBoxLayout(w)
        sp = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        ob = button("📂 Open PDF…")
        ob.clicked.connect(self.open_pdf)
        lv.addWidget(ob)
        lv.addWidget(QLabel("<b>Hydraulic schematics in your index</b>"))
        self.find = QLineEdit()
        self.find.setPlaceholderText("Filter…")
        self.find.textChanged.connect(self.refresh)
        self.docs = QListWidget()
        self.docs.itemDoubleClicked.connect(lambda it: self.load_pdf(it.data(Qt.ItemDataRole.UserRole)))
        lv.addWidget(self.find)
        lv.addWidget(self.docs, 2)
        pr = QHBoxLayout()
        pr.addWidget(QLabel("Page"))
        self.page = QSpinBox()
        self.page.setMinimum(1)
        self.page.valueChanged.connect(self.on_page)
        self.pages_lbl = QLabel("/ –")
        pr.addWidget(self.page)
        pr.addWidget(self.pages_lbl)
        pr.addStretch()
        lv.addLayout(pr)
        lv.addWidget(QLabel("<b>Components on this page</b>"))
        self.comps = QListWidget()
        lv.addWidget(self.comps, 2)
        sp.addWidget(left)
        self.view = PdfView()
        self.view.zoneSelected.connect(self.on_zone)
        sp.addWidget(self.view)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(QLabel("<b>🤖 Explanation</b>"))
        self.out = QTextBrowser()
        self.out.setHtml("<p style='color:#5F6D7E'>Open a schematic, then drag a box around a zone.</p>")
        rv.addWidget(self.out, 1)
        self.q = QLineEdit()
        self.q.setPlaceholderText("Question about the zone, e.g. what happens if Y3 is de-energised?")
        self.q.returnPressed.connect(self.ask_zone)
        qb = button("Ask about this zone")
        qb.clicked.connect(self.ask_zone)
        rv.addWidget(self.q)
        rv.addWidget(qb)
        for t in ["What happens if the solenoids are de-energised?", "Why can the cylinder drift?",
                  "Why does the oil overheat?", "Servo valve hunting — what to check?"]:
            b = button(t, chip=True)
            b.clicked.connect(lambda _=False, x=t: (self.q.setText(x), self.ask_zone()))
            rv.addWidget(b)
        sp.addWidget(right)
        sp.setSizes([260, 760, 360])
        h.addWidget(sp)
        return w

    def refresh(self, *_):
        self.docs.clear()
        for r in self.ctx.db.files_by_dtype("hydraulic", self.find.text().strip(), 1000):
            if r["ext"] != "pdf":
                continue
            it = QListWidgetItem(f"{r['name']}\n{os.path.dirname(r['path'])}")
            it.setData(Qt.ItemDataRole.UserRole, r["path"])
            it.setToolTip(r["path"])
            self.docs.addItem(it)
        if self.docs.count() == 0:
            it = QListWidgetItem("(none recognised yet — use Open PDF…)")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.docs.addItem(it)

    def open_pdf(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open hydraulic schematic", "", "PDF (*.pdf)")
        if p:
            self.load_pdf(p)

    def load_pdf(self, path):
        if not path:
            return
        try:
            n = hydraulics.page_count(path)
        except Exception as e:
            QMessageBox.warning(self, "PDF", f"Cannot open this PDF:\n{e}")
            return
        self.pdf = path
        self.page.blockSignals(True)
        self.page.setMaximum(max(1, n))
        self.page.setValue(1)
        self.page.blockSignals(False)
        self.pages_lbl.setText(f"/ {n}")
        self.render_page(0)

    def on_page(self, v):
        if self.pdf:
            self.render_page(v - 1)

    def render_page(self, no):
        import fitz
        self.page_no, self.zone = no, None
        with fitz.open(self.pdf) as d:
            page = d[no]
            r = page.rect
            dpi = min(150, 6000 / max(r.width, r.height) * 72)
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
        self.view.set_image(img, dpi / 72)
        self.comps.clear()
        try:
            for c in hydraulics.page_components(self.pdf, no):
                self.comps.addItem(f"{c['tag']} — {c['type']}" + (f"  ({', '.join(c['values'])})" if c["values"] else ""))
        except Exception:
            pass
        if self.comps.count() == 0:
            self.comps.addItem("(no tags found as text — scanned drawing?)")
        self.out.setHtml(f"<p><b>{html.escape(os.path.basename(self.pdf))}</b> — page {no + 1}</p>"
                         "<p style='color:#5F6D7E'>Drag a box around a zone of the drawing.</p>")

    def on_zone(self, rect_pt: QRectF):
        self.zone = (rect_pt.x(), rect_pt.y(), rect_pt.x() + rect_pt.width(), rect_pt.y() + rect_pt.height())
        self.run_zone("")

    def ask_zone(self):
        if not self.pdf:
            return
        if self.zone is None:   # whole page
            import fitz
            with fitz.open(self.pdf) as d:
                r = d[self.page_no].rect
            self.zone = (r.x0, r.y0, r.x1, r.y1)
        self.run_zone(self.q.text().strip())

    def run_zone(self, question):
        self.out.setHtml("<p style='color:#5F6D7E'>🤖 Reading the zone (text, symbols, image)…</p>")
        self.ctx.runner.run(hydraulics.explain_zone, (self.ctx.db, self.ctx.ai, self.pdf, self.page_no, self.zone, question),
                            self.on_explained, self.on_error)

    def on_explained(self, res):
        comps = "".join(f"<li><b>{html.escape(c['tag'])}</b> — {html.escape(c['type'])} {html.escape(', '.join(c['values']))}</li>"
                        for c in res["components"])
        self.out.setHtml(md_to_html(res["text"]) + (f"<hr><b>Tags in the zone</b><ul>{comps}</ul>" if comps else "")
                         + ("" if res["ai"] else "<p style='color:#8A6100'>Tip: install the picture model "
                            "(ollama pull qwen2.5vl:7b) or use Online mode for a full explanation.</p>")
                         + "<p style='color:#5F6D7E;font-size:8.5pt'>AI reading of a drawing — always verify on the "
                           "schematic.</p>")

    def on_error(self, msg):
        self.out.setHtml(f"<p style='color:#C0392B'>⚠ {html.escape(msg)}</p>")

    # ---------------- calculators
    def _spin(self, val, lo, hi, dec=1, step=1.0):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(dec)
        s.setSingleStep(step)
        s.setValue(val)
        s.valueChanged.connect(self.calc)
        return s

    def _calc_tab(self):
        w = QWidget()
        g = QHBoxLayout(w)
        b1 = QGroupBox("Cylinder")
        f1 = QFormLayout(b1)
        self.c_d, self.c_r = self._spin(125, 10, 2000), self._spin(70, 0, 1500)
        self.c_p, self.c_q = self._spin(160, 1, 700), self._spin(60, 0.1, 5000)
        f1.addRow("Bore Ø (mm)", self.c_d)
        f1.addRow("Rod Ø (mm)", self.c_r)
        f1.addRow("Pressure (bar)", self.c_p)
        f1.addRow("Flow (l/min)", self.c_q)
        self.c_out = QLabel()
        f1.addRow(self.c_out)
        b2 = QGroupBox("Pump / motor")
        f2 = QFormLayout(b2)
        self.p_v, self.p_n = self._spin(71, 1, 2000), self._spin(1480, 100, 4000, 0, 10)
        self.p_p = self._spin(160, 1, 700)
        self.p_ev, self.p_et = self._spin(0.95, 0.5, 1, 2, 0.01), self._spin(0.85, 0.3, 1, 2, 0.01)
        for l, s in (("Displacement (cm³/rev)", self.p_v), ("Speed (rpm)", self.p_n), ("Pressure (bar)", self.p_p),
                     ("η volumetric", self.p_ev), ("η total", self.p_et)):
            f2.addRow(l, s)
        self.p_out = QLabel()
        f2.addRow(self.p_out)
        b3 = QGroupBox("Accumulator")
        f3 = QFormLayout(b3)
        self.a_v, self.a_0 = self._spin(32, 0.1, 1000), self._spin(90, 1, 600)
        self.a_1, self.a_2 = self._spin(120, 1, 700), self._spin(160, 1, 700)
        self.a_n = QComboBox()
        self.a_n.addItem("adiabatic (fast)", 1.4)
        self.a_n.addItem("isothermal (slow)", 1.0)
        self.a_n.currentIndexChanged.connect(self.calc)
        for l, s in (("Size (l)", self.a_v), ("Pre-charge N₂ (bar)", self.a_0), ("Min pressure (bar)", self.a_1),
                     ("Max pressure (bar)", self.a_2), ("Gas process", self.a_n)):
            f3.addRow(l, s)
        self.a_out = QLabel()
        self.a_out.setWordWrap(True)
        f3.addRow(self.a_out)
        b4 = QGroupBox("Oil cleanliness (ISO 4406, typical)")
        f4 = QVBoxLayout(b4)
        t = QTableWidget(len(hydraulics.ISO_TARGETS), 2)
        t.setHorizontalHeaderLabels(["Component", "Target"])
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i, (a, b) in enumerate(hydraulics.ISO_TARGETS):
            t.setItem(i, 0, QTableWidgetItem(a))
            t.setItem(i, 1, QTableWidgetItem(b))
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        f4.addWidget(t)
        f4.addWidget(sub("Always follow the component manufacturer's requirement."))
        for b in (b1, b2, b3, b4):
            g.addWidget(b)
        self.calc()
        return w

    def calc(self, *_):
        c = hydraulics.cylinder(self.c_d.value(), self.c_r.value(), self.c_p.value(), self.c_q.value())
        self.c_out.setText(f"Push <b>{c['push_kN']:.0f} kN</b> · Pull <b>{c['pull_kN']:.0f} kN</b><br>"
                           f"Speed extend <b>{c['v_ext_mm_s']:.0f}</b> / retract <b>{c['v_ret_mm_s']:.0f} mm/s</b><br>"
                           f"Area ratio {c['area_ratio']:.2f}")
        p = hydraulics.pump(self.p_v.value(), self.p_n.value(), self.p_p.value(), self.p_ev.value(), self.p_et.value())
        self.p_out.setText(f"Flow <b>{p['flow_lmin']:.1f} l/min</b><br>Motor power <b>{p['power_kW']:.1f} kW</b>")
        a = hydraulics.accumulator(self.a_v.value(), self.a_0.value(), self.a_1.value(), self.a_2.value(),
                                   self.a_n.currentData() or 1.4)
        self.a_out.setText(f"Usable volume <b>{a['usable_l']:.1f} l</b>" + (f"<br><span style='color:#9A5B00'>⚠ {a['warning']}</span>"
                                                                          if a["warning"] else ""))


# ================================================================== lessons learned page
class CasesPage(Page):
    COLS = ["Date", "Area", "Symptom", "Root cause", "Fix / action", "By"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Lessons learned"))
        self.v.addWidget(sub("Every solved problem becomes knowledge: the Steel Specialist uses these cases in its answers."))
        row = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Search cases: stopper, looper, telescoping…")
        self.filter.textChanged.connect(self.refresh)
        add = button("＋ New case")
        add.clicked.connect(self.add)
        ed = button("Edit", ghost=True)
        ed.clicked.connect(self.edit)
        de = button("Delete", ghost=True)
        de.clicked.connect(self.delete)
        ex = button("Export to Excel", ghost=True)
        ex.clicked.connect(self.export)
        for w in (self.filter, add, ed, de, ex):
            row.addWidget(w, 1 if w is self.filter else 0)
        self.v.addLayout(row)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setWordWrap(True)
        for j in (2, 3, 4):
            self.table.horizontalHeader().setSectionResizeMode(j, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(lambda r, c: self.edit())
        self.v.addWidget(self.table, 1)
        self.rows = []

    def refresh(self, *_):
        self.rows = self.ctx.db.cases(self.filter.text().strip())
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            for j, k in enumerate(("date", "area", "symptom", "cause", "fix", "author")):
                val = AREA_NAMES.get(r[k], r[k]) if k == "area" else (r[k] or "")
                self.table.setItem(i, j, QTableWidgetItem(val))
        self.table.resizeRowsToContents()

    def current(self):
        i = self.table.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def add(self):
        if edit_case(self, self.ctx.db):
            self.refresh()

    def edit(self):
        c = self.current()
        if c and edit_case(self, self.ctx.db, case=c):
            self.refresh()

    def delete(self):
        c = self.current()
        if c and QMessageBox.question(self, "Delete", f"Delete this case?\n\n{c['symptom']}") == QMessageBox.StandardButton.Yes:
            self.ctx.db.case_delete(c["id"])
            self.refresh()

    def export(self):
        export_rows_xlsx(self, self.COLS, [(r["date"], AREA_NAMES.get(r["area"], r["area"]), r["symptom"], r["cause"],
                                            r["fix"], r["author"]) for r in self.rows], "lessons_learned.xlsx")
