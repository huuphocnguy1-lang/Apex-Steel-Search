"""All application pages."""
import html
import os
import re
import shutil

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QBrush, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPlainTextEdit, QProgressBar, QScrollArea, QSplitter, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import meta, search
from .common import (PreviewWidget, badge_html, button, fmt_date, fmt_size, h1, load_thumb_image, md_to_html,
                     open_file, placeholder, rev_html, sub, thumb_pixmap)


class Page(QWidget):
    title = ""

    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self.dirty = True
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(22, 18, 22, 14)
        self.v.setSpacing(10)

    def on_show(self):
        if self.dirty:
            self.dirty = False
            self.refresh()

    def refresh(self):
        pass


def export_rows_xlsx(parent, headers, rows, default_name):
    path, _ = QFileDialog.getSaveFileName(parent, "Export to Excel", default_name, "Excel (*.xlsx)")
    if not path:
        return
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E79")
    for r in rows:
        ws.append(list(r))
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(60, max(10, max(len(str(c.value or "")) for c in col) + 2))
    ws.freeze_panes = "A2"
    try:
        wb.save(path)
        open_file(path)
    except OSError as e:
        QMessageBox.warning(parent, "Export", f"Could not save: {e}")


# ================================================================== search
class SearchPage(Page):
    def __init__(self, ctx, smart=False):
        super().__init__(ctx)
        self.smart = smart
        self.results = []
        if smart:
            self.v.addWidget(h1("Smart search"))
            self.v.addWidget(sub("Search by meaning, in any language: “column foot fixing” also finds anchor bolts, "
                                 "tiges d'ancrage and 地脚螺栓. Needs the AI engine (see Settings)."))
        else:
            self.v.addWidget(h1("Keyword search"))
            self.v.addWidget(sub("Words inside every file: PDF, Word, Excel, emails, DWG/DXF title blocks, and text read "
                                 "by OCR from photos and scans."))
        row = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Describe what you are looking for…" if smart else
                                  "Words, drawing number, bolt size…  e.g. anchor bolt, M24 10.9, 螺栓")
        self.q.returnPressed.connect(self.do_search)
        go = button("Search")
        go.clicked.connect(self.do_search)
        row.addWidget(self.q, 1)
        row.addWidget(go)
        self.v.addLayout(row)
        chips = QHBoxLayout()
        ex = (["column foot fixing", "how tight should the crane bolts be", "paint thickness", "problem with bolt position"]
              if smart else ["anchor bolt", "M24 10.9", "grout", "torque", "螺栓", "IP55"])
        chips.addWidget(QLabel("Try:"))
        for e in ex:
            b = button(e, chip=True)
            b.clicked.connect(lambda _=False, t=e: self.search_text(t))
            chips.addWidget(b)
        chips.addStretch()
        self.v.addLayout(chips)
        f = QHBoxLayout()
        self.kind = QComboBox()
        for label, key in search.FILTER_KINDS:
            self.kind.addItem(label, key)
        self.project = QComboBox()
        self.latest = QCheckBox("Latest revision only")
        self.sort = QComboBox()
        self.sort.addItem("Sort: relevance", "rel")
        self.sort.addItem("Sort: newest", "date")
        exp = button("Export to Excel", ghost=True)
        exp.clicked.connect(self.export)
        for w in (self.kind, self.project, self.latest, self.sort):
            f.addWidget(w)
        f.addStretch()
        f.addWidget(exp)
        self.kind.currentIndexChanged.connect(self.do_search)
        self.project.currentIndexChanged.connect(self.do_search)
        self.latest.toggled.connect(self.do_search)
        self.sort.currentIndexChanged.connect(self.do_search)
        self.v.addLayout(f)
        self.info = sub("")
        self.v.addWidget(self.info)
        sp = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setObjectName("results")
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.currentRowChanged.connect(self.on_select)
        self.list.itemDoubleClicked.connect(self.on_double)
        self.preview = PreviewWidget(ctx)
        sp.addWidget(self.list)
        sp.addWidget(self.preview)
        sp.setSizes([650, 450])
        self.v.addWidget(sp, 1)

    def refresh(self):
        cur = self.project.currentData()
        self.project.blockSignals(True)
        self.project.clear()
        self.project.addItem("All projects", "all")
        for p in self.ctx.db.projects():
            self.project.addItem(p, p)
        i = self.project.findData(cur)
        self.project.setCurrentIndex(max(0, i))
        self.project.blockSignals(False)

    def filters(self):
        return {"kind": self.kind.currentData(), "project": self.project.currentData(),
                "latest": self.latest.isChecked(), "sort": self.sort.currentData()}

    def search_text(self, text):
        self.q.setText(text)
        self.do_search()

    def do_search(self, *_):
        q = self.q.text().strip()
        if not q:
            return
        self.info.setText("Searching…")
        if self.smart:
            self.ctx.runner.run(search.smart_search, (self.ctx.db, self.ctx.ai, q, self.filters()),
                                self.on_results, self.on_error)
        else:
            self.on_results(search.keyword_search(self.ctx.db, q, self.filters()))

    def on_error(self, msg):
        self.info.setText(f"⚠ {msg}")
        if self.smart:
            self.info.setText(f"⚠ Smart search not available: {msg}  —  showing keyword results instead.")
            self.on_results(search.keyword_search(self.ctx.db, self.q.text().strip(), self.filters()), keep_info=True)

    def on_results(self, res, keep_info=False):
        self.results = res["results"]
        self.list.clear()
        self.preview.clear()
        if not keep_info:
            self.info.setText(res.get("note", "") or "No result")
        for d in self.results:
            it = QListWidgetItem()
            w = QLabel()
            w.setTextFormat(Qt.TextFormat.RichText)
            w.setWordWrap(True)
            w.setContentsMargins(8, 6, 8, 6)
            reasons = "".join(f'&nbsp;<span style="background:#E8F0F8;color:#1F4E79;font-size:8pt">&nbsp;≈ {html.escape(x)}&nbsp;</span>'
                              for x in d.get("reasons", []))
            ocr = '&nbsp;<span style="background:#FFF4D6;color:#8A6100;font-size:8pt;font-weight:700">&nbsp;OCR&nbsp;</span>' if d.get("ocr") else ""
            w.setText(
                f'<table width="100%"><tr><td>{badge_html(d["ext"])}&nbsp;<b>{search.highlight_html(d["name"], d["terms"])}</b>'
                f'{rev_html(d["latest"], d["rev"])}{ocr}{reasons}<br>'
                f'<span style="color:#5F6D7E;font-size:8.5pt">{html.escape(os.path.dirname(d["path"]))} · {fmt_date(d["mtime"])} · {fmt_size(d["size"])}</span><br>'
                f'<span style="font-size:9pt">{search.highlight_html(d["snippet"], d["terms"])}</span></td>'
                f'<td align="right" width="70" style="color:#1F4E79"><b>{html.escape(d["label"].split(" ")[0])}</b><br>'
                f'<span style="color:#5F6D7E;font-size:8pt">{html.escape(" ".join(d["label"].split(" ")[1:]))}</span></td></tr></table>')
            it.setData(Qt.ItemDataRole.UserRole, d["id"])
            self.list.addItem(it)
            self.list.setItemWidget(it, w)
            it.setSizeHint(QSize(100, w.sizeHint().height() + 6))
        if self.results:
            self.list.setCurrentRow(0)

    def on_select(self, row):
        if 0 <= row < len(self.results):
            d = self.results[row]
            self.preview.set_file(d["id"], d["terms"])

    def on_double(self, item):
        r = self.ctx.db.get(item.data(Qt.ItemDataRole.UserRole))
        if r:
            open_file(r["path"])

    def export(self):
        if not self.results:
            return
        export_rows_xlsx(self, ["File", "Project", "Drawing no.", "Rev", "Latest", "Date", "Score", "Extract", "Path"],
                         [(d["name"], d["project"], d["dno"], d["rev"],
                           "" if d["latest"] is None else ("yes" if d["latest"] else "no"),
                           fmt_date(d["mtime"]), d["label"], d["snippet"], d["path"]) for d in self.results],
                         "search_results.xlsx")


# ================================================================== assistant
class AssistantPage(Page):
    SUGGEST = ["What bolt grade and torque for the crane girder connections?",
               "What changed in the latest revision of the column base drawing?",
               "How long before loading after grouting?",
               "List the non-conformances about anchor bolts"]

    def __init__(self, ctx):
        super().__init__(ctx)
        top = QHBoxLayout()
        top.addWidget(h1("AI assistant"))
        top.addStretch()
        self.model = sub("")
        top.addWidget(self.model)
        clr = button("New chat", ghost=True)
        clr.clicked.connect(self.clear)
        top.addWidget(clr)
        self.v.addLayout(top)
        self.v.addWidget(sub("Ask questions about your documents. Every answer lists its sources — click [1], [2]… "
                             "to open the exact file."))
        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self.on_link)
        self.v.addWidget(self.view, 1)
        chips = QHBoxLayout()
        for s in self.SUGGEST:
            b = button(s, chip=True)
            b.clicked.connect(lambda _=False, t=s: self.ask(t))
            chips.addWidget(b)
        chips.addStretch()
        self.v.addLayout(chips)
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Ask a question about your documents…")
        self.inp.returnPressed.connect(self.on_send)
        self.send = button("Send")
        self.send.clicked.connect(self.on_send)
        row.addWidget(self.inp, 1)
        row.addWidget(self.send)
        self.v.addLayout(row)
        self.history, self.parts, self.busy = [], [], False
        self.clear()

    def refresh(self):
        self.model.setText("Model: " + self.ctx.ai.chat_model_label())

    def on_show(self):
        self.refresh()
        self.inp.setFocus()

    def clear(self):
        self.history, self.parts = [], []
        self.render('<p style="color:#5F6D7E">Ask anything about your indexed documents. '
                    'Offline answers use the local model (Ollama); Online uses the cloud model.</p>')

    def render(self, extra=""):
        self.view.setHtml("".join(self.parts) + extra)
        sb = self.view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_send(self):
        t = self.inp.text().strip()
        if t:
            self.inp.clear()
            self.ask(t)

    def ask(self, q):
        if self.busy:
            return
        self.busy = True
        self.send.setEnabled(False)
        self.parts.append(f'<table width="100%" style="margin:6px 0"><tr><td width="25%"></td>'
                          f'<td style="background:#1F4E79;color:white;padding:8px 12px">{html.escape(q)}</td></tr></table>')
        self.render('<p style="color:#5F6D7E">🤖 Thinking… (' + html.escape(self.ctx.ai.chat_model_label()) + ')</p>')
        self._q = q
        self.ctx.runner.run(search.answer, (self.ctx.db, self.ctx.ai, q, list(self.history)), self.on_answer, self.on_error)

    def on_answer(self, res):
        self.busy = False
        self.send.setEnabled(True)
        body = md_to_html(res["text"])
        ids = {str(n): fid for n, fid, _ in res["sources"]}
        body = re.sub(r'href="cite:(\d+)"', lambda m: f'href="src:{ids.get(m.group(1), 0)}"', body)
        src = "".join(f'<div><a href="src:{fid}" style="color:#5F6D7E;text-decoration:none">[{n}] {html.escape(name)}</a></div>'
                      for n, fid, name in res["sources"])
        self.parts.append(f'<table width="100%" style="margin:6px 0"><tr><td style="background:white;border:1px solid #E1E6ED;padding:10px 12px">'
                          f'<span style="color:#5F6D7E;font-size:8.5pt">🤖 Apex AI · {html.escape(self.ctx.ai.chat_model_label())}</span><br>{body}'
                          + (f'<hr><span style="font-size:8.5pt"><b>Sources</b>{src}</span>' if src else "") +
                          '</td><td width="15%"></td></tr></table>')
        self.history += [{"role": "user", "content": self._q}, {"role": "assistant", "content": res["text"]}]
        self.render()

    def on_error(self, msg):
        self.busy = False
        self.send.setEnabled(True)
        self.parts.append(f'<p style="color:#C0392B">⚠ {html.escape(msg)}<br><span style="color:#5F6D7E">'
                          'Offline: install Ollama and run “ollama pull qwen2.5:7b” and “ollama pull bge-m3”. '
                          'Online: set your API key in Settings.</span></p>')
        self.render()

    def on_link(self, url: QUrl):
        s = url.toString()
        if s.startswith("src:"):
            try:
                fid = int(s[4:])
            except ValueError:
                return
            if fid:
                self.ctx.show_file(fid)


# ================================================================== library
class LibraryPage(Page):
    COLS = ["File", "Type", "Project", "Drawing no.", "Rev", "Latest", "Material", "Lang", "OCR", "Date", "Size", "Folder"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Library & tags"))
        self.v.addWidget(sub("Information found automatically in each file. Click a column to sort, double-click to open."))
        row = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter by name, drawing number, project…")
        self.filter.textChanged.connect(self._delay)
        self.count = sub("")
        exp = button("Export to Excel", ghost=True)
        exp.clicked.connect(self.export)
        row.addWidget(self.filter, 1)
        row.addWidget(self.count)
        row.addWidget(exp)
        self.v.addLayout(row)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self.on_double)
        self.v.addWidget(self.table, 1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.refresh)
        self.rows = []

    def _delay(self, *_):
        self.timer.start(300)

    def refresh(self):
        self.rows = self.ctx.db.library_rows(self.filter.text().strip())
        latest = self.ctx.db.latest_revs()
        t = self.table
        t.setSortingEnabled(False)
        t.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            lat = "" if not r["dno"] else ("✓" if latest.get(r["dno"]) == r["rev"] else "old")
            vals = [r["name"], r["ext"].upper(), r["project"] or "", r["dno"] or "", r["rev"] or "", lat,
                    r["material"] or "", r["lang"] or "", "yes" if r["ocr"] else "", fmt_date(r["mtime"]),
                    fmt_size(r["size"]), os.path.dirname(r["path"])]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if j == 0:
                    it.setData(Qt.ItemDataRole.UserRole, r["id"])
                    it.setToolTip(r["path"])
                t.setItem(i, j, it)
        t.setSortingEnabled(True)
        for j in range(1, len(self.COLS) - 1):
            t.resizeColumnToContents(j)
        self.count.setText(f"{len(self.rows)} file(s)" + (" (first 5000)" if len(self.rows) >= 5000 else ""))

    def on_double(self, row, col):
        it = self.table.item(row, 0)
        if it:
            self.ctx.show_file(it.data(Qt.ItemDataRole.UserRole))

    def export(self):
        latest = self.ctx.db.latest_revs()
        export_rows_xlsx(self, self.COLS[:-1] + ["Path"],
                         [(r["name"], r["ext"].upper(), r["project"], r["dno"], r["rev"],
                           "" if not r["dno"] else ("yes" if latest.get(r["dno"]) == r["rev"] else "no"),
                           r["material"], r["lang"], "yes" if r["ocr"] else "", fmt_date(r["mtime"]),
                           fmt_size(r["size"]), r["path"]) for r in self.rows], "library.xlsx")


# ================================================================== revisions
class RevisionsPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Revisions"))
        self.v.addWidget(sub("Every revision of each drawing, grouped automatically from the drawing number. "
                             "The latest is flagged ✓ so you never build from an old one."))
        sp = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter drawings…")
        self.filter.textChanged.connect(self.refresh)
        self.groups = QListWidget()
        self.groups.currentItemChanged.connect(self.on_group)
        lv.addWidget(self.filter)
        lv.addWidget(self.groups, 1)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Rev", "Status", "Date", "File", "Folder"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self.on_double)
        self.table.setMaximumHeight(200)
        cmp_row = QHBoxLayout()
        self.old = QComboBox()
        self.new = QComboBox()
        b = button("Compare")
        b.clicked.connect(self.compare)
        cmp_row.addWidget(QLabel("Old:"))
        cmp_row.addWidget(self.old)
        cmp_row.addWidget(QLabel("New:"))
        cmp_row.addWidget(self.new)
        cmp_row.addWidget(b)
        cmp_row.addStretch()
        self.diff = QTextBrowser()
        rv.addWidget(self.table)
        rv.addLayout(cmp_row)
        rv.addWidget(self.diff, 1)
        sp.addWidget(left)
        sp.addWidget(right)
        sp.setSizes([300, 700])
        self.v.addWidget(sp, 1)
        self.revs = []

    def refresh(self, *_):
        cur = self.groups.currentItem().data(Qt.ItemDataRole.UserRole) if self.groups.currentItem() else None
        self.groups.clear()
        for g in self.ctx.db.revision_groups(self.filter.text().strip()):
            it = QListWidgetItem(f"{g['dno']}   ·  {g['nrev']} rev\n{(g['title'] or '')[:60]}")
            it.setData(Qt.ItemDataRole.UserRole, g["dno"])
            self.groups.addItem(it)
            if g["dno"] == cur:
                self.groups.setCurrentItem(it)
        if self.groups.currentItem() is None and self.groups.count():
            self.groups.setCurrentRow(0)

    def on_group(self, it, _prev=None):
        if it is None:
            return
        self.revs = self.ctx.db.revisions(it.data(Qt.ItemDataRole.UserRole))
        latest = self.revs[-1]["rev"] if self.revs else None
        self.table.setRowCount(len(self.revs))
        self.old.clear()
        self.new.clear()
        for i, r in enumerate(self.revs):
            st = "✓ Latest" if r["rev"] == latest else "Superseded"
            for j, val in enumerate([r["rev"] or "?", st, fmt_date(r["mtime"]), r["name"], os.path.dirname(r["path"])]):
                cell = QTableWidgetItem(val)
                if j == 1 and r["rev"] == latest:
                    cell.setForeground(QBrush(QColor("#1E8E5A")))
                self.table.setItem(i, j, cell)
            label = f"Rev {r['rev']} · {fmt_date(r['mtime'])} · {r['name']}"
            self.old.addItem(label, r["id"])
            self.new.addItem(label, r["id"])
        self.table.resizeColumnsToContents()
        if len(self.revs) >= 2:
            self.old.setCurrentIndex(len(self.revs) - 2)
            self.new.setCurrentIndex(len(self.revs) - 1)
            self.compare()
        else:
            self.diff.setHtml('<p style="color:#5F6D7E">Only one revision of this drawing is indexed.</p>')

    def compare(self):
        a, b = self.old.currentData(), self.new.currentData()
        if not a or not b:
            return
        ra, rb = self.ctx.db.get(a), self.ctx.db.get(b)
        if a == b:
            self.diff.setHtml('<p style="color:#5F6D7E">Choose two different files.</p>')
            return
        lines = search.diff_texts(self.ctx.db.body(a), self.ctx.db.body(b))
        changes = [x for x in lines if x[0] != "same"]
        out = [f"<h3>Changes Rev {html.escape(ra['rev'] or '?')} → Rev {html.escape(rb['rev'] or '?')}</h3>"]
        if not changes:
            out.append('<p style="color:#5F6D7E">No text difference found (the change may be graphic only — '
                       'open both files to check).</p>')
        style = {"add": "background:#E3F4EC;color:#14603D", "del": "background:#FBE7E4;color:#8E2A1F;text-decoration:line-through",
                 "same": "color:#8A96A3"}
        sign = {"add": "＋ ", "del": "－ ", "same": ""}
        for k, s in lines:
            out.append(f'<p style="{style[k]};margin:2px 0;padding:3px 6px">{sign[k]}{html.escape(s)}</p>')
        self.diff.setHtml("".join(out))

    def on_double(self, row, col):
        if 0 <= row < len(self.revs):
            self.ctx.show_file(self.revs[row]["id"])


# ================================================================== photos
class PhotosPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Photos & OCR"))
        self.v.addWidget(sub("Text in photos is read automatically (Chinese, English, French). "
                             "Select a photo to see its text, or find similar photos."))
        row = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Search text seen in photos, e.g. A3, 75 kW, serial number…")
        self.filter.returnPressed.connect(self.refresh)
        b1 = button("Search")
        b1.clicked.connect(self.refresh)
        b2 = button("📷 Find photos like this one…", ghost=True)
        b2.clicked.connect(self.search_by_photo)
        b3 = button("Show all", ghost=True)
        b3.clicked.connect(self.show_all)
        for w in (self.filter, b1, b2, b3):
            row.addWidget(w, 1 if w is self.filter else 0)
        self.v.addLayout(row)
        self.info = sub("")
        self.v.addWidget(self.info)
        sp = QSplitter(Qt.Orientation.Horizontal)
        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setIconSize(QSize(180, 130))
        self.grid.setGridSize(QSize(200, 170))
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setMovement(QListWidget.Movement.Static)
        self.grid.setWordWrap(True)
        self.grid.currentItemChanged.connect(self.on_pick)
        self.grid.itemDoubleClicked.connect(lambda it: self.ctx.show_file(it.data(Qt.ItemDataRole.UserRole)))
        side = QWidget()
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        self.big = QLabel("Select a photo")
        self.big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.big.setMinimumHeight(220)
        self.big.setStyleSheet("background:white;border:1px solid #E1E6ED;border-radius:8px")
        self.name = QLabel()
        self.name.setWordWrap(True)
        self.ocr = QTextBrowser()
        brow = QHBoxLayout()
        self.b_sim = button("Find similar photos")
        self.b_sim.clicked.connect(self.find_similar)
        self.b_open = button("Open", ghost=True)
        self.b_open.clicked.connect(lambda: self.cur and open_file(self.cur["path"]))
        brow.addWidget(self.b_sim)
        brow.addWidget(self.b_open)
        brow.addStretch()
        sv.addWidget(self.big)
        sv.addWidget(self.name)
        sv.addWidget(QLabel("<b>Text found (OCR)</b>"))
        sv.addWidget(self.ocr, 1)
        sv.addLayout(brow)
        sp.addWidget(self.grid)
        sp.addWidget(side)
        sp.setSizes([700, 380])
        self.v.addWidget(sp, 1)
        self.cur = None
        self.queue = []
        self.loader = QTimer(self)
        self.loader.timeout.connect(self._load_some)

    def show_all(self):
        self.filter.clear()
        self.refresh()

    def refresh(self, *_):
        rows = self.ctx.db.photos(self.filter.text().strip())
        self.info.setText(f"{len(rows)} photo(s)" + (" — newest 400 shown" if len(rows) >= 400 else ""))
        self.fill([(r, None) for r in rows])

    def fill(self, items):
        self.grid.clear()
        self.queue = []
        ph = QIcon(placeholder("jpg", QSize(180, 130)))
        for r, score in items:
            label = (f"{score}% similar\n" if score is not None else "") + f"{r['name']}\n{fmt_date(r['mtime'])}"
            it = QListWidgetItem(ph, label)
            it.setData(Qt.ItemDataRole.UserRole, r["id"])
            it.setToolTip(r["path"])
            self.grid.addItem(it)
            self.queue.append((it, r["path"], r["ext"]))
        self.loader.start(15)

    def _load_some(self):
        for _ in range(6):
            if not self.queue:
                self.loader.stop()
                return
            it, path, ext = self.queue.pop(0)
            img = load_thumb_image(path, ext, 180, 130)
            if img is not None:
                it.setIcon(QIcon(QPixmap.fromImage(img)))

    def on_pick(self, it, _prev=None):
        if it is None:
            return
        r = self.ctx.db.get(it.data(Qt.ItemDataRole.UserRole))
        if r is None:
            return
        self.cur = r
        self.big.setPixmap(thumb_pixmap(r["path"], r["ext"], 380, 260))
        self.name.setText(f"<b>{html.escape(r['name'])}</b><br><span style='color:#5F6D7E'>{html.escape(r['path'])}</span>")
        body = self.ctx.db.body(r["id"])
        self.ocr.setPlainText(body or ("No text found." if r["ocr"] == 0 else ""))

    def _rank(self, ph, exclude=None):
        ranked = []
        for row in self.ctx.db.all_photo_hashes():
            if row["id"] == exclude:
                continue
            d = meta.hamming(ph, row["phash"])
            ranked.append((d, row["id"]))
        ranked.sort()
        items = []
        for d, fid in ranked[:80]:
            r = self.ctx.db.get(fid)
            if r:
                items.append((r, max(0, round(100 - d * 100 / 40))))
        return items

    def find_similar(self):
        if not self.cur or not self.cur["phash"]:
            return
        self.info.setText(f"Photos similar to {self.cur['name']}")
        self.fill(self._rank(self.cur["phash"], self.cur["id"]))

    def search_by_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a photo", "", "Images (*.jpg *.jpeg *.png *.bmp *.webp *.tif)")
        if not path:
            return
        from PIL import Image, ImageOps
        try:
            with Image.open(path) as im:
                ph = meta.dhash(ImageOps.exif_transpose(im))
        except Exception as e:
            QMessageBox.warning(self, "Photo", f"Cannot read this image: {e}")
            return
        self.info.setText(f"Photos similar to {os.path.basename(path)}")
        self.fill(self._rank(ph))


# ================================================================== duplicates
class DuplicatesPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Duplicates"))
        self.v.addWidget(sub("Identical files saved in several places (Downloads, WeChat, USB copies…). "
                             "Tick the copies you don't need and move them to a “_to_delete” folder."))
        row = QHBoxLayout()
        self.info = sub("")
        b = button("Move ticked copies to _to_delete")
        b.clicked.connect(self.move_checked)
        r = button("Refresh", ghost=True)
        r.clicked.connect(self.refresh)
        row.addWidget(self.info, 1)
        row.addWidget(r)
        row.addWidget(b)
        self.v.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File", "Folder", "Date", "Size"])
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.itemDoubleClicked.connect(self.on_double)
        self.v.addWidget(self.tree, 1)

    def refresh(self):
        self.tree.clear()
        groups = self.ctx.db.duplicate_groups()
        wasted = 0
        for g in groups:
            top = QTreeWidgetItem([f"{g[0]['title'] or g[0]['name']}  —  {len(g)} copies", "", "", fmt_size(g[0]["size"])])
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            for i, r in enumerate(g):
                c = QTreeWidgetItem([r["name"], os.path.dirname(r["path"]), fmt_date(r["mtime"]), fmt_size(r["size"])])
                c.setData(0, Qt.ItemDataRole.UserRole, r["id"])
                c.setData(1, Qt.ItemDataRole.UserRole, r["path"])
                c.setCheckState(0, Qt.CheckState.Unchecked)
                top.addChild(c)
            wasted += g[0]["size"] * (len(g) - 1)
            top.setExpanded(True)
        for j in (0, 2, 3):
            self.tree.resizeColumnToContents(j)
        self.info.setText(f"{len(groups)} group(s) of identical files · {fmt_size(wasted)} could be freed"
                          if groups else "No duplicates found 🎉")

    def move_checked(self):
        paths = []
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                c = top.child(j)
                if c.checkState(0) == Qt.CheckState.Checked:
                    paths.append(c.data(1, Qt.ItemDataRole.UserRole))
        if not paths:
            QMessageBox.information(self, "Duplicates", "Tick the copies you want to remove first.")
            return
        if QMessageBox.question(self, "Move copies", f"Move {len(paths)} file(s) to a “_to_delete” folder next to them?\n"
                                "You can delete that folder yourself later.") != QMessageBox.StandardButton.Yes:
            return
        moved = 0
        for p in paths:
            try:
                dest_dir = os.path.join(os.path.dirname(p), "_to_delete")
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, os.path.basename(p))
                base, ext = os.path.splitext(dest)
                n = 1
                while os.path.exists(dest):
                    dest = f"{base} ({n}){ext}"
                    n += 1
                shutil.move(p, dest)
                self.ctx.db.delete_path(p)
                moved += 1
            except OSError as e:
                QMessageBox.warning(self, "Move", f"Could not move {p}:\n{e}")
        self.ctx.set_status(f"{moved} file(s) moved to _to_delete")
        self.refresh()

    def on_double(self, item, col):
        fid = item.data(0, Qt.ItemDataRole.UserRole)
        if fid:
            self.ctx.show_file(fid)


# ================================================================== folders
class FoldersPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Folders & index"))
        self.v.addWidget(sub("Choose the folders to watch. New and changed files are indexed automatically in the "
                             "background — only changed files are read again."))
        self.stats = QLabel()
        self.stats.setObjectName("card")
        self.stats.setTextFormat(Qt.TextFormat.RichText)
        self.v.addWidget(self.stats)
        sp = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(QLabel("<b>Watched folders</b> (untick to pause a folder)"))
        self.folders = QListWidget()
        self.folders.itemChanged.connect(self.on_folder_toggled)
        lv.addWidget(self.folders, 1)
        fr = QHBoxLayout()
        add = button("＋ Add folder")
        add.clicked.connect(self.add_folder)
        rem = button("Remove", ghost=True)
        rem.clicked.connect(self.remove_folder)
        fr.addWidget(add)
        fr.addWidget(rem)
        fr.addStretch()
        lv.addLayout(fr)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(QLabel("<b>Indexing</b>"))
        br = QHBoxLayout()
        self.b_scan = button("Re-index now")
        self.b_scan.clicked.connect(lambda: self.ctx.worker.enqueue(("scan",)))
        self.b_smart = button("🧠 Build smart index", ghost=True,
                              tip="Creates the AI index used by Smart search and the assistant (needs Ollama or cloud)")
        self.b_smart.clicked.connect(lambda: self.ctx.worker.enqueue(("embed",)))
        self.b_stop = button("Stop", ghost=True)
        self.b_stop.clicked.connect(self.ctx.worker.cancel)
        for b in (self.b_scan, self.b_smart, self.b_stop):
            br.addWidget(b)
        br.addStretch()
        rv.addLayout(br)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.state = sub("Idle")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        self.log.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt")
        rv.addWidget(self.bar)
        rv.addWidget(self.state)
        rv.addWidget(self.log, 1)
        rv.addWidget(sub("Supported: PDF · Word · Excel · CSV · PowerPoint · TXT · Outlook .msg/.eml · DXF · "
                         "DWG (with ODA File Converter) · JPG/PNG/TIF/HEIC photos and scanned PDFs (OCR)."))
        sp.addWidget(left)
        sp.addWidget(right)
        sp.setSizes([420, 600])
        self.v.addWidget(sp, 1)

    def refresh(self):
        self.folders.blockSignals(True)
        self.folders.clear()
        for f in self.ctx.cfg.get("folders", []):
            it = QListWidgetItem(("📁  " if os.path.isdir(f["path"]) else "⚠  ") + f["path"])
            it.setData(Qt.ItemDataRole.UserRole, f["path"])
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if f.get("enabled", True) else Qt.CheckState.Unchecked)
            if not os.path.isdir(f["path"]):
                it.setToolTip("Folder not found (USB drive unplugged?)")
            self.folders.addItem(it)
        self.folders.blockSignals(False)
        s = self.ctx.db.stats()
        cell = lambda n, l: (f'<td style="padding:4px 18px 4px 0"><span style="font-size:17pt;font-weight:700;color:#1F4E79">{n}</span>'
                             f'<br><span style="color:#5F6D7E">{l}</span></td>')
        self.stats.setText("<table><tr>" + cell(s["total"], "files indexed") + cell(s.get("drawing", 0), "drawings") +
                           cell(s.get("photo", 0), "photos") + cell(s["ocr"], "read by OCR") +
                           cell(f"{s['vectors']}/{s['chunks']}", "smart index passages") +
                           cell(f"{s['db_mb']} MB", "index size") + cell(s["errors"], "with notes") + "</tr></table>")

    def append_log(self, msg):
        self.log.appendPlainText(msg)

    def set_progress(self, i, n, name):
        self.bar.setValue(int(i * 100 / n) if n else 100)
        self.state.setText(f"{i}/{n}  {name}" if name else "Idle")

    def _save_folders(self):
        self.ctx.cfg.save()
        self.ctx.folders_changed()
        self.refresh()

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Choose a folder to index")
        if not d:
            return
        d = os.path.normpath(d)
        if any(os.path.normcase(f["path"]) == os.path.normcase(d) for f in self.ctx.cfg["folders"]):
            return
        self.ctx.cfg["folders"] = self.ctx.cfg["folders"] + [{"path": d, "enabled": True}]
        self._save_folders()

    def remove_folder(self):
        it = self.folders.currentItem()
        if not it:
            return
        p = it.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Remove folder", f"Stop indexing this folder?\n{p}\n\n(Your files are not touched.)") \
                != QMessageBox.StandardButton.Yes:
            return
        self.ctx.cfg["folders"] = [f for f in self.ctx.cfg["folders"] if f["path"] != p]
        self._save_folders()

    def on_folder_toggled(self, it):
        p = it.data(Qt.ItemDataRole.UserRole)
        for f in self.ctx.cfg["folders"]:
            if f["path"] == p:
                f["enabled"] = it.checkState() == Qt.CheckState.Checked
        self.ctx.cfg.save()
        self.ctx.folders_changed()


# ================================================================== settings
class SettingsPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("Settings"))
        self.v.addWidget(sub("Everything works offline. Online mode only adds the cloud AI for the assistant."))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("page")
        form = QFormLayout(inner)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        c = ctx.cfg
        self.mode = QComboBox()
        self.mode.addItem("🔒 Offline — everything on this laptop", "offline")
        self.mode.addItem("☁ Online — assistant uses the cloud AI", "online")
        self.ollama = QLineEdit(c["ollama_url"])
        self.lchat = QLineEdit(c["local_chat_model"])
        self.lemb = QLineEdit(c["local_embed_model"])
        self.cbase = QLineEdit(c["cloud_base_url"])
        self.ckey = QLineEdit(c["cloud_api_key"])
        self.ckey.setEchoMode(QLineEdit.EchoMode.Password)
        self.cchat = QLineEdit(c["cloud_chat_model"])
        self.cemb = QLineEdit(c["cloud_embed_model"])
        self.eprov = QComboBox()
        self.eprov.addItem("Local (Ollama) — recommended, offline", "local")
        self.eprov.addItem("Cloud", "cloud")
        self.auto = QCheckBox("Build smart index automatically after each scan")
        self.ocr = QCheckBox("Read text in photos and scanned PDFs (OCR)")
        self.oda = QLineEdit(c["oda_path"])
        oda_b = button("Browse…", ghost=True)
        oda_b.clicked.connect(self.browse_oda)
        oda_row = QHBoxLayout()
        oda_row.addWidget(self.oda, 1)
        oda_row.addWidget(oda_b)
        self.preg = QLineEdit(c["project_regex"])
        self.excl = QLineEdit(", ".join(c["excluded_dirs"]))

        def section(t):
            lb = QLabel(f"<b style='color:#1F4E79;font-size:11pt'>{t}</b>")
            lb.setContentsMargins(0, 10, 0, 0)
            form.addRow(lb)

        section("General")
        form.addRow("Mode", self.mode)
        section("Offline AI (Ollama)")
        form.addRow("Ollama address", self.ollama)
        form.addRow("Chat model", self.lchat)
        form.addRow("Smart search model", self.lemb)
        form.addRow("", sub("Install Ollama from ollama.com, then run:  ollama pull qwen2.5:7b   and   ollama pull bge-m3"))
        section("Online AI (OpenAI-compatible: Qwen / DeepSeek …)")
        form.addRow("API address", self.cbase)
        form.addRow("API key", self.ckey)
        form.addRow("Chat model", self.cchat)
        form.addRow("Embedding model", self.cemb)
        section("Smart index")
        form.addRow("Built with", self.eprov)
        form.addRow("", self.auto)
        section("Reading files")
        form.addRow("", self.ocr)
        form.addRow("ODA File Converter (DWG)", oda_row)
        form.addRow("Project code pattern", self.preg)
        form.addRow("Skip folders named", self.excl)
        row = QHBoxLayout()
        save = button("Save settings")
        save.clicked.connect(self.save)
        test = button("Test AI connection", ghost=True)
        test.clicked.connect(self.test)
        row.addWidget(save)
        row.addWidget(test)
        row.addStretch()
        form.addRow("", row)
        self.result = QLabel()
        self.result.setWordWrap(True)
        form.addRow("", self.result)
        scroll.setWidget(inner)
        self.v.addWidget(scroll, 1)

    def refresh(self):
        c = self.ctx.cfg
        self.mode.setCurrentIndex(max(0, self.mode.findData(c["mode"])))
        self.eprov.setCurrentIndex(max(0, self.eprov.findData(c["embed_provider"])))
        self.auto.setChecked(bool(c["auto_smart"]))
        self.ocr.setChecked(bool(c["ocr_enabled"]))

    def browse_oda(self):
        p, _ = QFileDialog.getOpenFileName(self, "ODAFileConverter.exe", self.oda.text(), "Programs (*.exe)")
        if p:
            self.oda.setText(os.path.normpath(p))

    def save(self):
        c = self.ctx.cfg
        c.update(mode=self.mode.currentData(), ollama_url=self.ollama.text().strip(),
                 local_chat_model=self.lchat.text().strip(), local_embed_model=self.lemb.text().strip(),
                 cloud_base_url=self.cbase.text().strip(), cloud_api_key=self.ckey.text().strip(),
                 cloud_chat_model=self.cchat.text().strip(), cloud_embed_model=self.cemb.text().strip(),
                 embed_provider=self.eprov.currentData(), auto_smart=self.auto.isChecked(),
                 ocr_enabled=self.ocr.isChecked(), oda_path=self.oda.text().strip(),
                 project_regex=self.preg.text().strip() or r"\bP-?\d{3,5}\b",
                 excluded_dirs=[x.strip() for x in self.excl.text().split(",") if x.strip()])
        c.save()
        self.ctx.mode_changed()
        self.result.setText("✔ Saved.")

    def test(self):
        self.save()
        self.result.setText("Testing… (the first call can take a minute while the model loads)")
        self.ctx.runner.run(self.ctx.ai.test, (), self.on_test, self.on_test)

    def on_test(self, msg):
        self.result.setText(str(msg).replace("\n", "<br>"))
