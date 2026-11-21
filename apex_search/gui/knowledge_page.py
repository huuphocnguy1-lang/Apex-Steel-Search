"""📚 Knowledge page: built-in expert notes + Learn from web → offline specialist answers."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar, QSpinBox,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .. import knowledge
from .common import button, h1, open_file, sub
from .pages import Page

ROLE_KEY = int(Qt.ItemDataRole.UserRole) + 1   # web-source key stored in the table


class KnowledgePage(Page):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.v.addWidget(h1("📚 Knowledge — make the AI a specialist"))
        self.v.addWidget(sub("The AI answers from a knowledge library, offline, with sources. Priority: 🏭 your plant "
                             "documents → 📒 lessons learned → 📘 built-in expert notes → 🌐 web sources → 🤖 AI notes. "
                             "Learn from the web when you are online; the night analysis digests everything."))
        self.stats = QLabel()
        self.stats.setObjectName("card")
        self.stats.setTextFormat(Qt.TextFormat.RichText)
        self.v.addWidget(self.stats)
        sp = QSplitter(Qt.Orientation.Horizontal)

        # ---------------- left: what to learn
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(QLabel("<b>Topic packs</b> (tick what to learn from the web)"))
        self.packs = QListWidget()
        lv.addWidget(self.packs, 1)
        lv.addWidget(QLabel("<b>Your own topics</b> (one per line, e.g. 'HGC servo valve hunting')"))
        self.custom = QPlainTextEdit()
        self.custom.setMaximumHeight(70)
        lv.addWidget(self.custom)
        lv.addWidget(QLabel("<b>Web pages / PDF links to add</b> (one per line)"))
        self.urls = QPlainTextEdit()
        self.urls.setMaximumHeight(60)
        self.urls.setPlaceholderText("https://…")
        lv.addWidget(self.urls)
        opt = QHBoxLayout()
        opt.addWidget(QLabel("Pages per search"))
        self.per = QSpinBox()
        self.per.setRange(1, 5)
        opt.addWidget(self.per)
        opt.addWidget(QLabel("Search engine"))
        self.engine = QComboBox()
        for k, l in (("auto", "Auto (Bing → Bing China → DuckDuckGo)"), ("bing", "Bing"), ("bing_cn", "Bing China"),
                     ("ddg", "DuckDuckGo")):
            self.engine.addItem(l, k)
        opt.addWidget(self.engine, 1)
        lv.addLayout(opt)
        self.wiki = QCheckBox("Also Wikipedia")
        self.ainotes = QCheckBox("Also ask the Online AI to write a note per topic (marked 'unverified')")
        lv.addWidget(self.wiki)
        lv.addWidget(self.ainotes)
        br = QHBoxLayout()
        self.b_learn = button("🌐 Learn from web")
        self.b_learn.clicked.connect(self.start_learn)
        self.b_digest = button("🌙 Digest now", ghost=True, tip="Index + smart index + summaries of the knowledge folder")
        self.b_digest.clicked.connect(lambda: self.ctx.worker.enqueue(("digest",)))
        self.b_stop = button("Stop", ghost=True)
        self.b_stop.clicked.connect(self.ctx.worker.cancel)
        self.b_folder = button("📁 Open folder", ghost=True,
                               tip="Put your own manuals in 'my_notes' — they count as plant documents")
        self.b_folder.clicked.connect(lambda: open_file(knowledge.root()))
        for b in (self.b_learn, self.b_digest, self.b_stop, self.b_folder):
            br.addWidget(b)
        br.addStretch()
        lv.addLayout(br)

        # ---------------- right: library + log
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(QLabel("<b>Library</b> (double-click to open)"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Source", "Topic", "Type", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.open_row)
        rv.addWidget(self.table, 2)
        rr = QHBoxLayout()
        rem = button("Remove selected web source", ghost=True)
        rem.clicked.connect(self.remove_selected)
        rr.addWidget(rem)
        rr.addStretch()
        rv.addLayout(rr)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        rv.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt")
        rv.addWidget(self.log, 1)
        sp.addWidget(left)
        sp.addWidget(right)
        sp.setSizes([480, 640])
        self.v.addWidget(sp, 1)

    # ------------------------------------------------------------------
    def refresh(self):
        c = self.ctx.cfg
        counts = knowledge.counts_by_topic()
        chosen = set(c.get("kn_topics", []))
        self.packs.clear()
        for k, (label, kw, qs) in knowledge.PACKS.items():
            it = QListWidgetItem(f"{label}   ·   {len(qs)} searches   ·   {counts.get(k, 0)} learned")
            it.setData(Qt.ItemDataRole.UserRole, k)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if k in chosen else Qt.CheckState.Unchecked)
            self.packs.addItem(it)
        self.per.setValue(int(c.get("kn_per_query", 2)))
        self.engine.setCurrentIndex(max(0, self.engine.findData(c.get("kn_engine", "auto"))))
        self.wiki.setChecked(bool(c.get("kn_wikipedia", True)))
        self.ainotes.setChecked(bool(c.get("kn_ai_notes", False)))
        rows = []
        for p in knowledge.builtin_files():
            rows.append((os.path.basename(p)[3:-3].replace("_", " "), "built-in", "📘 expert note", "", p))
        for key, e in sorted(knowledge.load_manifest().items(), key=lambda kv: kv[1].get("date", ""), reverse=True):
            rows.append((e.get("title", "")[:120], e.get("topic", ""), "🌐 web", e.get("date", ""), e.get("file", ""), key))
        root = knowledge.root()
        for sub_, typ in (("ai_notes", "🤖 AI note"), ("my_notes", "🏭 my note")):
            for dp, _, fs in os.walk(os.path.join(root, sub_)):
                for f in fs:
                    rows.append((f, os.path.basename(dp), typ, "", os.path.join(dp, f)))
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j in range(4):
                it = QTableWidgetItem(r[j])
                if j == 0:
                    it.setData(Qt.ItemDataRole.UserRole, r[4])
                    it.setData(ROLE_KEY, r[5] if len(r) > 5 else None)
                self.table.setItem(i, j, it)
        nb = len(knowledge.builtin_files())
        nw = len(knowledge.load_manifest())
        done, total = self.ctx.db.count_to_summarise([root])
        cell = lambda n, l: (f'<td style="padding:4px 18px 4px 0"><span style="font-size:17pt;font-weight:700;color:#1F4E79">'
                             f'{n}</span><br><span style="color:#5F6D7E">{l}</span></td>')
        self.stats.setText("<table><tr>" + cell(nb, "built-in expert notes") + cell(nw, "web sources learned") +
                           cell(f"{done}/{total}", "digested (summaries)") + "</tr></table>")

    def on_show(self):
        self.refresh()

    def _save_opts(self):
        c = self.ctx.cfg
        c["kn_topics"] = [self.packs.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.packs.count())
                          if self.packs.item(i).checkState() == Qt.CheckState.Checked]
        c["kn_per_query"] = self.per.value()
        c["kn_engine"] = self.engine.currentData()
        c["kn_wikipedia"] = self.wiki.isChecked()
        c["kn_ai_notes"] = self.ainotes.isChecked()
        c.save()

    def start_learn(self):
        self._save_opts()
        c = self.ctx.cfg
        custom = [x for x in self.custom.toPlainText().splitlines() if x.strip()]
        urls = [x.strip() for x in self.urls.toPlainText().splitlines() if x.strip().startswith("http")]
        if not c["kn_topics"] and not custom and not urls:
            QMessageBox.information(self, "Knowledge", "Tick at least one topic pack, or type a topic / link.")
            return
        if c["kn_ai_notes"] and not self.ctx.ai.online:
            self.append_log("Note: AI notes need the ☁ Online mode with an API key — they will be skipped.")
        nq = sum(len(knowledge.PACKS[t][2]) for t in c["kn_topics"]) + len(custom)
        self.append_log(f"Queued: {nq} searches, {len(urls)} links. Pages are saved in {knowledge.root()}")
        self.ctx.worker.enqueue(("learn", {"topics": c["kn_topics"], "custom": custom, "urls": urls,
                                           "per_query": c["kn_per_query"], "engine": c["kn_engine"],
                                           "wikipedia": c["kn_wikipedia"],
                                           "ai_notes": bool(c["kn_ai_notes"] and self.ctx.ai.online)}))

    def open_row(self, r, _c):
        it = self.table.item(r, 0)
        p = it.data(Qt.ItemDataRole.UserRole) if it else None
        if p and os.path.exists(p):
            open_file(p)

    def remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedItems()})
        n = 0
        for r in rows:
            key = self.table.item(r, 0).data(ROLE_KEY)
            if key:
                knowledge.remove_source(key)
                n += 1
        if n:
            self.append_log(f"Removed {n} web source(s); the index updates automatically.")
            self.ctx.worker.enqueue(("digest",))
        self.refresh()

    def append_log(self, msg):
        self.log.appendPlainText(msg)

    def set_progress(self, i, n, msg):
        self.bar.setValue(int(100 * i / n) if n else 0)
