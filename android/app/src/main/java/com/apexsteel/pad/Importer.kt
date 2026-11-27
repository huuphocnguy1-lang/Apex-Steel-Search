package com.apexsteel.pad

import android.content.ContentResolver
import android.database.sqlite.SQLiteDatabase
import android.net.Uri
import java.io.File
import java.io.FileOutputStream
import java.util.Locale
import java.util.zip.ZipInputStream

/** Imports the .apexpad file exported by Apex Steel Analyser (Windows): titles, text extracts, summaries,
 *  drawing types. Rows are matched to the files on the pad by name (+ size); the others stay searchable as
 *  'only on laptop'. */
class Importer(private val resolver: ContentResolver, private val db: PadDb, private val cacheDir: File) {

    fun import(uri: Uri, progress: (String) -> Unit): Int {
        progress("Reading the laptop index…")
        val dbFile = File(cacheDir, "pad_index.db")
        if (dbFile.exists()) dbFile.delete()
        var ok = false
        resolver.openInputStream(uri)?.use { input ->
            ZipInputStream(input).use { zip ->
                var e = zip.nextEntry
                while (e != null) {
                    if (e.name.endsWith("pad_index.db")) {
                        FileOutputStream(dbFile).use { out -> zip.copyTo(out, 1 shl 16) }
                        ok = true
                        break
                    }
                    e = zip.nextEntry
                }
            }
        }
        if (!ok) throw IllegalArgumentException("This is not an .apexpad file (pad_index.db not found).")
        val src = SQLiteDatabase.openDatabase(dbFile.path, null, SQLiteDatabase.OPEN_READONLY)
        val w = db.writableDatabase
        var n = 0
        w.beginTransaction()
        try {
            w.execSQL("DELETE FROM docs WHERE onpad=0")        // a new laptop index replaces the previous one
            val ins = w.compileStatement(
                "INSERT INTO docs(uri, tree, relpath, name, lname, ext, size, mtime, dno, rev, title, dtype, summary, " +
                    "body, onpad, seen) VALUES (NULL,NULL,?,?,?,?,?,?,?,?,?,?,?,?,0,1)"
            )
            src.rawQuery(
                "SELECT name, relpath, size, mtime, ext, dtype, dno, rev, title, summary, body FROM docs", null
            ).use { c ->
                while (c.moveToNext()) {
                    val name = c.getString(0) ?: continue
                    ins.clearBindings()
                    ins.bindString(1, c.getString(1) ?: name)
                    ins.bindString(2, name)
                    ins.bindString(3, name.lowercase(Locale.ROOT))
                    ins.bindString(4, (c.getString(4) ?: Names.ext(name)).lowercase(Locale.ROOT))
                    ins.bindLong(5, if (c.isNull(2)) 0 else c.getLong(2))
                    ins.bindLong(6, if (c.isNull(3)) 0 else (c.getDouble(3) * 1000).toLong())
                    for ((i, col) in listOf(6, 7, 8, 5, 9, 10).withIndex()) {
                        val v = c.getString(col)
                        if (v != null) ins.bindString(7 + i, v) else ins.bindNull(7 + i)
                    }
                    ins.executeInsert()
                    n++
                    if (n % 2000 == 0) progress("Importing… $n documents")
                }
            }
            progress("Matching with the files on this pad…")
            db.mergeLaptopRows(w)
            w.setTransactionSuccessful()
        } finally {
            w.endTransaction()
            src.close()
            dbFile.delete()
        }
        return n
    }
}
