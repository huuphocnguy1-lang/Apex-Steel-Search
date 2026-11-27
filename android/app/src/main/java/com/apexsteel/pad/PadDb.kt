package com.apexsteel.pad

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.util.Locale

data class Doc(
    val id: Long,
    val uri: String?,
    val name: String,
    val relpath: String,
    val ext: String,
    val size: Long,
    val mtime: Long,
    val dno: String?,
    val rev: String?,
    val title: String?,
    val dtype: String?,
    val summary: String?,
    val body: String?,
    val onPad: Boolean,
)

/** Local index on the pad. docs = every file found on the pad (+ rows imported from the laptop index);
 *  fts = full-text index (FTS4) over name, number, title + summary, text. */
class PadDb(context: Context) : SQLiteOpenHelper(context, "pad.db", null, 2) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE docs(id INTEGER PRIMARY KEY, uri TEXT, tree TEXT, relpath TEXT, name TEXT, lname TEXT,
               ext TEXT, size INTEGER, mtime INTEGER, dno TEXT, rev TEXT, title TEXT, dtype TEXT, summary TEXT,
               body TEXT, onpad INTEGER, seen INTEGER, readst INTEGER DEFAULT 0)"""
        )
        db.execSQL("CREATE UNIQUE INDEX ix_docs_uri ON docs(uri)")
        db.execSQL("CREATE INDEX ix_docs_lname ON docs(lname)")
        db.execSQL("CREATE INDEX ix_docs_tree ON docs(tree)")
        db.execSQL("CREATE VIRTUAL TABLE fts USING fts4(name, dno, info, body, tokenize=unicode61)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) db.execSQL("ALTER TABLE docs ADD COLUMN readst INTEGER DEFAULT 0")
    }

    // ------------------------------------------------------------------ 📖 reading documents on the pad
    data class ToRead(val id: Long, val uri: String, val ext: String, val size: Long)

    /** Files on the pad not read yet (readst = 0) whose type can be read. */
    fun toRead(exts: Set<String>): List<ToRead> {
        val out = ArrayList<ToRead>()
        val inList = exts.joinToString(",") { "'$it'" }
        readableDatabase.rawQuery(
            "SELECT id, uri, ext, size FROM docs WHERE onpad=1 AND readst=0 AND uri IS NOT NULL AND ext IN ($inList) " +
                "ORDER BY mtime DESC", null
        ).use { c ->
            while (c.moveToNext()) out.add(ToRead(c.getLong(0), c.getString(1), c.getString(2) ?: "", c.getLong(3)))
        }
        return out
    }

    /** Saves text read on the pad. Keeps text imported from the laptop when the pad finds none. */
    fun setRead(id: Long, text: String?, ok: Boolean) {
        val w = writableDatabase
        if (!text.isNullOrBlank()) {
            w.execSQL(
                "UPDATE docs SET body = CASE WHEN body IS NULL OR body = '' THEN ? ELSE body || char(10) || ? END, readst=1 WHERE id=?",
                arrayOf<Any>(text, text.take(4000), id)
            )
        } else {
            w.execSQL("UPDATE docs SET readst=? WHERE id=?", arrayOf<Any>(if (ok) 1 else -1, id))
        }
    }

    fun readCount(): Int {
        readableDatabase.rawQuery("SELECT COUNT(*) FROM docs WHERE onpad=1 AND readst=1", null).use { c ->
            return if (c.moveToFirst()) c.getInt(0) else 0
        }
    }

    fun count(): Pair<Int, Int> {
        val db = readableDatabase
        var pad = 0
        var laptop = 0
        db.rawQuery("SELECT onpad, COUNT(*) FROM docs GROUP BY onpad", null).use { c ->
            while (c.moveToNext()) {
                if (c.getInt(0) == 1) pad = c.getInt(1) else laptop = c.getInt(1)
            }
        }
        return Pair(pad, laptop)
    }

    fun rebuildFts() {
        val db = writableDatabase
        db.beginTransaction()
        try {
            db.execSQL("DELETE FROM fts")
            db.execSQL(
                """INSERT INTO fts(docid, name, dno, info, body) SELECT id, replace(replace(name,'_',' '),'-',' '),
                   coalesce(dno,''), coalesce(title,'') || ' ' || coalesce(summary,''), coalesce(body,'') FROM docs"""
            )
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    /** Copies laptop information (title, text, summary, type) onto pad files with the same name (+ size). */
    fun mergeLaptopRows(db: SQLiteDatabase = writableDatabase) {
        db.execSQL(
            """UPDATE docs SET
                 title = coalesce((SELECT l.title FROM docs l WHERE l.onpad=0 AND l.lname=docs.lname ORDER BY (l.size=docs.size) DESC LIMIT 1), title),
                 summary = coalesce((SELECT l.summary FROM docs l WHERE l.onpad=0 AND l.lname=docs.lname ORDER BY (l.size=docs.size) DESC LIMIT 1), summary),
                 body = coalesce((SELECT l.body FROM docs l WHERE l.onpad=0 AND l.lname=docs.lname ORDER BY (l.size=docs.size) DESC LIMIT 1), body),
                 dtype = coalesce((SELECT l.dtype FROM docs l WHERE l.onpad=0 AND l.lname=docs.lname ORDER BY (l.size=docs.size) DESC LIMIT 1), dtype),
                 dno = coalesce((SELECT l.dno FROM docs l WHERE l.onpad=0 AND l.lname=docs.lname AND l.dno IS NOT NULL LIMIT 1), dno),
                 rev = coalesce((SELECT l.rev FROM docs l WHERE l.onpad=0 AND l.lname=docs.lname AND l.rev IS NOT NULL LIMIT 1), rev)
               WHERE onpad=1 AND EXISTS (SELECT 1 FROM docs l WHERE l.onpad=0 AND l.lname=docs.lname)"""
        )
        // laptop rows now represented by a pad file are not needed any more
        db.execSQL("DELETE FROM docs WHERE onpad=0 AND lname IN (SELECT lname FROM docs WHERE onpad=1)")
    }

    // ------------------------------------------------------------------ search
    enum class Filter { ALL, DRAWINGS, HYDRAULIC, PDF, WORD, EXCEL, PHOTOS }

    private fun filterSql(f: Filter): String = when (f) {
        Filter.ALL -> ""
        Filter.DRAWINGS -> " AND (d.ext IN ('dwg','dxf') OR d.dtype IN ('mechanical','hydraulic','pid','electrical','drawing') OR (d.ext='pdf' AND d.dno IS NOT NULL))"
        Filter.HYDRAULIC -> " AND (d.dtype='hydraulic' OR d.lname LIKE '%hydraul%' OR d.lname LIKE '%液压%' OR d.lname LIKE '%hpu%')"
        Filter.PDF -> " AND d.ext='pdf'"
        Filter.WORD -> " AND d.ext IN ('doc','docx','rtf','odt')"
        Filter.EXCEL -> " AND d.ext IN ('xls','xlsx','xlsm','csv','ods')"
        Filter.PHOTOS -> " AND d.ext IN ('jpg','jpeg','png','heic','bmp','webp','tif','tiff')"
    }

    private val cols = "d.id, d.uri, d.name, d.relpath, d.ext, d.size, d.mtime, d.dno, d.rev, d.title, d.dtype, " +
        "d.summary, substr(d.body, 1, 3000), d.onpad"

    private fun read(sql: String, args: Array<String>): List<Doc> {
        val out = ArrayList<Doc>()
        readableDatabase.rawQuery(sql, args).use { c ->
            while (c.moveToNext()) {
                out.add(
                    Doc(
                        c.getLong(0), c.getString(1), c.getString(2) ?: "", c.getString(3) ?: "", c.getString(4) ?: "",
                        c.getLong(5), c.getLong(6), c.getString(7), c.getString(8), c.getString(9), c.getString(10),
                        c.getString(11), c.getString(12), c.getInt(13) == 1
                    )
                )
            }
        }
        return out
    }

    private fun hasCjk(s: String) = s.any { Character.UnicodeScript.of(it.code) == Character.UnicodeScript.HAN }

    /** SQL condition for one synonym group: any of its words in name / number / title / summary / text. */
    private fun groupCond(g: List<String>, args: ArrayList<String>): String {
        val parts = ArrayList<String>()
        val short = g.filter { Synonyms.isShortWord(it) }
        if (short.isNotEmpty()) {
            parts.add("d.id IN (SELECT docid FROM fts WHERE fts MATCH ?)")
            args.add(short.joinToString(" OR "))
        }
        for (w in g.filter { !Synonyms.isShortWord(it) }) {
            val like = "%" + w.lowercase(Locale.ROOT) + "%"
            parts.add("(d.lname LIKE ? OR lower(coalesce(d.title,'')) LIKE ? OR lower(coalesce(d.summary,'')) LIKE ? OR lower(coalesce(d.body,'')) LIKE ?)")
            repeat(4) { args.add(like) }
        }
        return "(" + parts.joinToString(" OR ") + ")"
    }

    fun search(query: String, filter: Filter, limit: Int = 300): List<Doc> {
        val q = query.trim()
        val fsql = filterSql(filter)
        if (q.isEmpty()) {
            return read("SELECT $cols FROM docs d WHERE 1=1$fsql ORDER BY d.onpad DESC, d.mtime DESC LIMIT $limit", arrayOf())
        }
        val ex = Synonyms.expand(q)
        val results = LinkedHashMap<Long, Doc>()
        val terms = ex.rest.lowercase(Locale.ROOT).split(Regex("""[^\p{L}\p{N}]+""")).filter { it.isNotBlank() }
        if (ex.groups.isNotEmpty()) {
            // synonym search: every group must match (any of its words); remaining words via the FTS index
            val args = ArrayList<String>()
            val conds = ex.groups.map { groupCond(it, args) }.toMutableList()
            if (terms.isNotEmpty() && !hasCjk(ex.rest)) {
                conds.add("d.id IN (SELECT docid FROM fts WHERE fts MATCH ?)")
                args.add(terms.joinToString(" ") { "$it*" })
            } else if (terms.isNotEmpty()) {
                val like = "%" + ex.rest.lowercase(Locale.ROOT) + "%"
                conds.add("(d.lname LIKE ? OR lower(coalesce(d.title,'')) LIKE ? OR lower(coalesce(d.body,'')) LIKE ?)")
                repeat(3) { args.add(like) }
            }
            try {
                for (d in read(
                    "SELECT $cols FROM docs d WHERE ${conds.joinToString(" AND ")}$fsql ORDER BY d.onpad DESC, d.mtime DESC LIMIT $limit",
                    args.toTypedArray()
                )) results[d.id] = d
            } catch (e: Exception) {
                // fall back to the normal search below
            }
            if (results.isNotEmpty()) return results.values.take(limit)
        }
        if (terms.isNotEmpty() && !hasCjk(q)) {
            val allTerms = q.lowercase(Locale.ROOT).split(Regex("""[^\p{L}\p{N}]+""")).filter { it.isNotBlank() }
            val match = allTerms.joinToString(" ") { "$it*" }
            try {
                for (d in read(
                    "SELECT $cols FROM fts JOIN docs d ON d.id=fts.docid WHERE fts MATCH ?$fsql ORDER BY d.onpad DESC LIMIT $limit",
                    arrayOf(match)
                )) results[d.id] = d
            } catch (e: Exception) {
                // malformed FTS query → LIKE search below
            }
        }
        if (results.size < limit) {
            // substring search in names / numbers / titles (finds '0302' inside 'F0302', Chinese words, …)
            val like = "%" + q.lowercase(Locale.ROOT).replace("%", "").replace("_", "\\_") + "%"
            val extra = read(
                "SELECT $cols FROM docs d WHERE (d.lname LIKE ? ESCAPE '\\' OR lower(coalesce(d.dno,'')) LIKE ? ESCAPE '\\' " +
                    "OR lower(coalesce(d.title,'')) LIKE ? ESCAPE '\\' OR lower(coalesce(d.summary,'')) LIKE ? ESCAPE '\\')$fsql " +
                    "ORDER BY d.onpad DESC, d.mtime DESC LIMIT $limit",
                arrayOf(like, like, like, like)
            )
            for (d in extra) if (!results.containsKey(d.id)) results[d.id] = d
            if (results.size < 20 && hasCjk(q)) {
                for (d in read("SELECT $cols FROM docs d WHERE d.body LIKE ?$fsql LIMIT 100", arrayOf("%$q%"))) results[d.id] = d
            }
        }
        return results.values.take(limit)
    }

    /** Keeps only the highest revision of each drawing number. */
    fun latestOnly(docs: List<Doc>): List<Doc> {
        val best = HashMap<String, Doc>()
        val out = ArrayList<Doc>()
        for (d in docs) {
            val key = d.dno?.lowercase(Locale.ROOT)
            if (key.isNullOrBlank()) continue
            val b = best[key]
            if (b == null || Names.compareRev(d.rev, b.rev) > 0) best[key] = d
        }
        for (d in docs) {
            val key = d.dno?.lowercase(Locale.ROOT)
            if (key.isNullOrBlank() || best[key]?.id == d.id) out.add(d)
        }
        return out
    }

    fun values(d: Map<String, Any?>): ContentValues {
        val v = ContentValues()
        for ((k, x) in d) {
            when (x) {
                null -> v.putNull(k)
                is String -> v.put(k, x)
                is Long -> v.put(k, x)
                is Int -> v.put(k, x)
                is Double -> v.put(k, x)
                else -> v.put(k, x.toString())
            }
        }
        return v
    }
}
