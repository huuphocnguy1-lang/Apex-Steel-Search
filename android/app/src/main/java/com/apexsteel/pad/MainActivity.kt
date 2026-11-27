package com.apexsteel.pad

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import com.google.android.material.materialswitch.MaterialSwitch
import com.google.android.material.textfield.TextInputEditText
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

class MainActivity : AppCompatActivity() {

    private lateinit var db: PadDb
    private lateinit var adapter: DocAdapter
    private lateinit var search: TextInputEditText
    private lateinit var status: TextView
    private lateinit var progress: ProgressBar
    private lateinit var empty: TextView
    private lateinit var latest: MaterialSwitch
    private lateinit var synLine: TextView
    private lateinit var preview: PreviewPanel
    private val reading = AtomicBoolean(false)
    private val io = Executors.newSingleThreadExecutor()
    private val searchExec = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val stop = AtomicBoolean(false)
    private val searchSeq = AtomicInteger(0)
    private var filter = PadDb.Filter.ALL
    private val prefs by lazy { getSharedPreferences("apexpad", Context.MODE_PRIVATE) }

    private val pickFolder = registerForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
        if (uri != null) {
            try {
                contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            } catch (e: SecurityException) {
                // permission could not be kept: works until the app is closed
            }
            val set = trees().toMutableSet()
            set.add(uri.toString())
            prefs.edit().putStringSet("trees", set).apply()
            scan(listOf(uri))
        }
    }

    private val pickImport = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) importIndex(uri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        db = PadDb(this)
        val toolbar = findViewById<MaterialToolbar>(R.id.toolbar)
        setSupportActionBar(toolbar)
        search = findViewById(R.id.search)
        status = findViewById(R.id.status)
        progress = findViewById(R.id.progress)
        empty = findViewById(R.id.empty)
        latest = findViewById(R.id.latest)
        synLine = findViewById(R.id.synLine)
        val split = findViewById<LinearLayout>(R.id.split)
        if (resources.configuration.orientation == Configuration.ORIENTATION_PORTRAIT) {
            // portrait: list on top, preview below
            split.orientation = LinearLayout.VERTICAL
            for (id in intArrayOf(R.id.listBox, R.id.pv)) {
                val v = findViewById<View>(id)
                val lp = v.layoutParams as LinearLayout.LayoutParams
                lp.width = LinearLayout.LayoutParams.MATCH_PARENT
                lp.height = 0
                v.layoutParams = lp
            }
        }
        preview = PreviewPanel(findViewById(R.id.pv), contentResolver, ::open, ::share, ::copy)
        latest.isChecked = prefs.getBoolean("latest", false)
        latest.setOnCheckedChangeListener { _, on ->
            prefs.edit().putBoolean("latest", on).apply()
            runSearch()
        }

        adapter = DocAdapter(::tap, ::details)
        val list = findViewById<RecyclerView>(R.id.list)
        list.layoutManager = LinearLayoutManager(this)
        list.adapter = adapter

        val chips = findViewById<ChipGroup>(R.id.chips)
        val labels = listOf(
            "All" to PadDb.Filter.ALL, "Drawings" to PadDb.Filter.DRAWINGS, "Hydraulic" to PadDb.Filter.HYDRAULIC,
            "PDF" to PadDb.Filter.PDF, "Word" to PadDb.Filter.WORD, "Excel" to PadDb.Filter.EXCEL,
            "Photos" to PadDb.Filter.PHOTOS
        )
        for ((label, f) in labels) {
            val c = Chip(this)
            c.text = label
            c.isCheckable = true
            c.isChecked = f == PadDb.Filter.ALL
            c.setOnClickListener {
                filter = f
                for (i in 0 until chips.childCount) (chips.getChildAt(i) as Chip).isChecked = chips.getChildAt(i) == c
                runSearch()
            }
            chips.addView(c)
        }

        search.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                main.removeCallbacksAndMessages(SEARCH_TOKEN)
                main.postAtTime({ runSearch() }, SEARCH_TOKEN, android.os.SystemClock.uptimeMillis() + 250)
            }
        })
        search.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEARCH) {
                runSearch(); true
            } else false
        }

        runSearch()
        // update the index quietly at start (only changed files are written)
        if (trees().isNotEmpty()) scan(trees().map { Uri.parse(it) }, quiet = true)
    }

    override fun onDestroy() {
        stop.set(true)
        preview.release()
        super.onDestroy()
    }

    /** Tap = preview; tap again on the selected document = open it. */
    private fun tap(d: Doc) {
        if (adapter.selectedId == d.id) {
            open(d)
            return
        }
        adapter.selectedId = d.id
        preview.show(d)
    }

    private fun trees(): Set<String> = prefs.getStringSet("trees", emptySet()) ?: emptySet()

    // ------------------------------------------------------------------ menu
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            R.id.action_add -> pickFolder.launch(null)
            R.id.action_rescan -> if (trees().isEmpty()) pickFolder.launch(null) else scan(trees().map { Uri.parse(it) })
            R.id.action_import -> pickImport.launch(arrayOf("*/*"))
            R.id.action_read -> if (trees().isEmpty()) toast("Add a folder first (＋ Add folder)") else readDocs(false)
            R.id.action_syn -> showSynonyms()
            R.id.action_folders -> manageFolders()
            R.id.action_about -> about()
            else -> return super.onOptionsItemSelected(item)
        }
        return true
    }

    // ------------------------------------------------------------------ search
    private fun runSearch() {
        val q = search.text?.toString() ?: ""
        val f = filter
        val onlyLatest = latest.isChecked
        val seq = searchSeq.incrementAndGet()
        searchExec.execute {
            val res = try {
                val r = db.search(q, f)
                if (onlyLatest) db.latestOnly(r) else r
            } catch (e: Exception) {
                emptyList()
            }
            val (pad, laptop) = db.count()
            val nread = try { db.readCount() } catch (e: Exception) { 0 }
            val ex = Synonyms.expand(q)
            main.post {
                if (seq != searchSeq.get()) return@post
                adapter.submit(res, q)
                if (ex.groups.isEmpty()) {
                    synLine.visibility = View.GONE
                } else {
                    synLine.visibility = View.VISIBLE
                    synLine.text = "≈ also searching: " + ex.groups.joinToString("   |   ") { it.joinToString(" · ") }
                }
                empty.visibility = if (pad + laptop == 0) View.VISIBLE else View.GONE
                if (progress.visibility != View.VISIBLE) {
                    status.text = "${res.size}${if (res.size >= 300) "+" else ""} found  ·  $pad files on this pad" +
                        (if (nread > 0) "  ·  📖 $nread read" else "") +
                        (if (laptop > 0) "  ·  $laptop only on laptop" else "")
                }
            }
        }
    }

    // ------------------------------------------------------------------ scan / import
    private fun busy(text: String?) {
        main.post {
            if (text == null) {
                progress.visibility = View.GONE
                runSearch()
            } else {
                progress.visibility = View.VISIBLE
                status.text = text
            }
        }
    }

    private fun scan(uris: List<Uri>, quiet: Boolean = false) {
        if (!quiet) busy("Scanning…")
        io.execute {
            var total = 0
            val scanner = Scanner(contentResolver, db)
            val problems = ArrayList<String>()
            for (u in uris) {
                try {
                    val r = scanner.scanTree(u, { t -> if (!quiet) busy(t) }, { stop.get() })
                    total += r.files
                    if (r.files == 0) {
                        problems.add("• ${folderLabel(u.toString())}: ${r.dirs} folder(s) opened, 0 files" +
                            (if (r.errors > 0) ", ${r.errors} not readable (${r.firstError})" else ""))
                    }
                } catch (e: Exception) {
                    problems.add("• ${folderLabel(u.toString())}: cannot be read (${e.javaClass.simpleName}: ${e.message})")
                }
            }
            if (!quiet && problems.isNotEmpty()) main.post {
                AlertDialog.Builder(this)
                    .setTitle("No files found")
                    .setMessage(problems.joinToString("\n") + "\n\nCheck with the Xiaomi File Manager that your drawings are " +
                        "really in this folder. In the folder picker, choose the folder under 'Internal storage' (not Recent, " +
                        "Gallery or cloud). Android does not allow the storage root, Download itself or Android/data: put the " +
                        "drawings in e.g. Documents/your project and choose that folder.")
                    .setPositiveButton("Choose another folder") { _, _ -> pickFolder.launch(null) }
                    .setNegativeButton("OK", null).show()
            }
            if (!quiet) busy("Building search index…")
            try {
                db.rebuildFts()
            } catch (e: Exception) {
                main.post { toast("Index error: ${e.message}") }
            }
            busy(null)
            if (!quiet) main.post { toast("$total files indexed") }
            main.post { readDocs(true) }      // 📖 read the new / changed documents
        }
    }

    /** 📖 Reads the text inside the documents on the pad (PDF text layer, Word, Excel), new / changed files only. */
    private fun readDocs(auto: Boolean) {
        if (!reading.compareAndSet(false, true)) return
        io.execute {
            try {
                val todo = db.toRead(Reader.READABLE)
                if (todo.isEmpty()) {
                    if (!auto) main.post { toast("All documents are already read") }
                    return@execute
                }
                val reader = Reader(this, contentResolver)
                var n = 0
                var found = 0
                for (t in todo) {
                    if (stop.get()) break
                    n++
                    if (n % 5 == 1) busy("📖 Reading documents… $n / ${todo.size}  (PDF text, Word, Excel)")
                    try {
                        val text = reader.read(Uri.parse(t.uri), t.ext, t.size)
                        db.setRead(t.id, text, true)
                        if (text.isNotBlank()) found++
                    } catch (e: Throwable) {          // corrupt / protected file, out of memory on a huge PDF…
                        db.setRead(t.id, null, false)
                    }
                    if (n % 200 == 0) db.rebuildFts()
                }
                busy("Building search index…")
                db.rebuildFts()
                main.post { toast("📖 $n documents read — text found in $found. You can now search inside them.") }
            } finally {
                reading.set(false)
                busy(null)
            }
        }
    }

    private fun importIndex(uri: Uri) {
        busy("Importing laptop index…")
        io.execute {
            try {
                val n = Importer(contentResolver, db, cacheDir).import(uri) { t -> busy(t) }
                busy("Building search index…")
                db.rebuildFts()
                main.post { toast("Laptop index imported: $n documents") }
            } catch (e: Exception) {
                main.post { toast("Import failed: ${e.message}") }
            }
            busy(null)
        }
    }

    // ------------------------------------------------------------------ actions
    private fun open(d: Doc) {
        if (!d.onPad || d.uri == null) {
            AlertDialog.Builder(this)
                .setTitle("Only on the laptop")
                .setMessage("${d.name}\n\nLaptop path:\n${d.relpath}\n\nCopy this folder to the pad and add it with ＋ Add folder.")
                .setPositiveButton("OK", null)
                .setNeutralButton("Copy path") { _, _ -> copy(d.relpath) }
                .show()
            return
        }
        val uri = Uri.parse(d.uri)
        val type = contentResolver.getType(uri) ?: Names.mime(d.ext)
        val i = Intent(Intent.ACTION_VIEW).setDataAndType(uri, type).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        try {
            startActivity(i)
        } catch (e: ActivityNotFoundException) {
            try {
                startActivity(Intent.createChooser(Intent(Intent.ACTION_VIEW).setDataAndType(uri, "*/*")
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION), "Open with"))
            } catch (e2: Exception) {
                toast("No app can open .${d.ext} files — install a viewer (e.g. a DWG viewer for drawings).")
            }
        } catch (e: SecurityException) {
            toast("Access lost — add the folder again (＋ Add folder).")
        }
    }

    private fun share(d: Doc) {
        if (!d.onPad || d.uri == null) return
        val s = Intent(Intent.ACTION_SEND).setType(Names.mime(d.ext))
            .putExtra(Intent.EXTRA_STREAM, Uri.parse(d.uri)).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        try {
            startActivity(Intent.createChooser(s, "Share"))
        } catch (e: Exception) {
            toast("Cannot share this file")
        }
    }

    private fun showSynonyms() {
        AlertDialog.Builder(this)
            .setTitle("ESP synonyms")
            .setMessage(Synonyms.GROUPS.joinToString("\n") { "• " + it.joinToString(" · ") } +
                "\n\nTyping any word of a line also finds the others (any word order).")
            .setPositiveButton("OK", null).show()
    }

    private fun details(d: Doc) {
        val msg = buildString {
            append("Type: ").append(Names.typeLabel(d.ext, d.dtype)).append('\n')
            if (!d.dno.isNullOrBlank()) append("Number: ").append(d.dno).append('\n')
            if (!d.rev.isNullOrBlank()) append("Revision: ").append(d.rev).append('\n')
            if (!d.title.isNullOrBlank()) append("Title: ").append(d.title).append('\n')
            append("Path: ").append(d.relpath).append('\n')
            if (!d.summary.isNullOrBlank()) append("\nSummary:\n").append(d.summary)
        }
        val b = AlertDialog.Builder(this).setTitle(d.name).setMessage(msg)
            .setPositiveButton("Open") { _, _ -> open(d) }
            .setNeutralButton("Copy name") { _, _ -> copy(d.name) }
        if (d.onPad && d.uri != null) b.setNegativeButton("Share") { _, _ -> share(d) }
        b.show()
    }

    private fun manageFolders() {
        val list = trees().toList()
        if (list.isEmpty()) {
            pickFolder.launch(null)
            return
        }
        val names = list.map { folderLabel(it) }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle("Folders on this pad (tap to remove)")
            .setItems(names) { _, which ->
                AlertDialog.Builder(this).setTitle("Remove folder?").setMessage(names[which] +
                    "\n\nThe files stay on the pad; they are only removed from the search.")
                    .setPositiveButton("Remove") { _, _ ->
                        val t = list[which]
                        prefs.edit().putStringSet("trees", trees() - t).apply()
                        try {
                            contentResolver.releasePersistableUriPermission(Uri.parse(t), Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        } catch (e: Exception) {
                        }
                        io.execute {
                            Scanner(contentResolver, db).removeTree(t)
                            db.rebuildFts()
                            busy(null)
                        }
                    }
                    .setNegativeButton("Cancel", null).show()
            }
            .setPositiveButton("＋ Add folder") { _, _ -> pickFolder.launch(null) }
            .setNegativeButton("Close", null)
            .show()
    }

    private fun about() {
        AlertDialog.Builder(this)
            .setTitle("Apex Steel Pad ${BuildConfigVersion.NAME}")
            .setMessage(
                "Find drawings and documents on this pad.\n\n" +
                    "1. ＋ Add folder: choose the folder(s) with your drawings.\n" +
                    "2. 📖 Read: the pad reads the text inside PDF / Word / Excel (automatic after each scan).\n" +
                    "3. Type a drawing number, a name or a word — ESP synonyms are included (rotary shear = SHR = crop shear = 转鼓飞剪…).\n" +
                    "4. Tap = preview on the right · tap again or OPEN = full viewer.\n" +
                    "5. Optional: on the laptop, Apex Steel Analyser → Folders & index → 📱 Export for pad; " +
                    "copy the .apexpad file to the pad and use Import laptop index to search inside documents.\n\n" +
                    "Long-press = details / share."
            )
            .setPositiveButton("OK", null).show()
    }

    /** "content://…/tree/primary%3ADocuments%2FESP" → "Internal storage/Documents/ESP" */
    private fun folderLabel(tree: String): String {
        val id = try {
            android.provider.DocumentsContract.getTreeDocumentId(Uri.parse(tree))
        } catch (e: Exception) {
            Uri.decode(tree)
        }
        val vol = id.substringBefore(':', "")
        val path = id.substringAfter(':', id)
        return (if (vol == "primary") "Internal storage" else vol.ifBlank { "Storage" }) + "/" + path
    }

    private fun copy(text: String) {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("Apex", text))
        toast("Copied")
    }

    private fun toast(t: String) = Toast.makeText(this, t, Toast.LENGTH_LONG).show()

    companion object {
        private val SEARCH_TOKEN = Any()
    }
}

object BuildConfigVersion {
    const val NAME = "0.2.1"
}
