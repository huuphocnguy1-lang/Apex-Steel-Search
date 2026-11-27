package com.apexsteel.pad

import android.content.ContentResolver
import android.net.Uri
import android.provider.DocumentsContract
import java.util.Locale

/** Walks the folders chosen by the user (Storage Access Framework) and updates the local index. */
class Scanner(private val resolver: ContentResolver, private val db: PadDb) {

    data class Result(val files: Int, val dirs: Int, val errors: Int, val firstError: String?, val rootName: String)

    private data class Found(val uri: String, val relpath: String, val name: String, val size: Long, val mtime: Long)

    private val projection = arrayOf(
        DocumentsContract.Document.COLUMN_DOCUMENT_ID,
        DocumentsContract.Document.COLUMN_DISPLAY_NAME,
        DocumentsContract.Document.COLUMN_MIME_TYPE,
        DocumentsContract.Document.COLUMN_SIZE,
        DocumentsContract.Document.COLUMN_LAST_MODIFIED,
    )

    /** Returns the number of files found. progress(text) is called from the worker thread. */
    fun scanTree(treeUri: Uri, progress: (String) -> Unit, stop: () -> Boolean): Result {
        val found = ArrayList<Found>()
        val rootId = DocumentsContract.getTreeDocumentId(treeUri)
        val rootName = rootId.substringAfterLast(':').substringAfterLast('/').ifBlank { "Folder" }
        val stack = ArrayDeque<Pair<String, String>>()     // (documentId, relative path)
        stack.addLast(Pair(rootId, rootName))
        var dirs = 0
        var errors = 0
        var firstError: String? = null
        while (stack.isNotEmpty() && !stop()) {
            val (docId, rel) = stack.removeLast()
            val children = DocumentsContract.buildChildDocumentsUriUsingTree(treeUri, docId)
            try {
                resolver.query(children, projection, null, null, null)?.use { c ->
                    while (c.moveToNext()) {
                        val id = c.getString(0) ?: continue
                        val name = c.getString(1) ?: continue
                        val mime = c.getString(2) ?: ""
                        if (name.startsWith(".")) continue
                        if (mime == DocumentsContract.Document.MIME_TYPE_DIR) {
                            stack.addLast(Pair(id, "$rel/$name"))
                        } else {
                            val uri = DocumentsContract.buildDocumentUriUsingTree(treeUri, id).toString()
                            found.add(Found(uri, "$rel/$name", name, if (c.isNull(3)) 0 else c.getLong(3),
                                if (c.isNull(4)) 0 else c.getLong(4)))
                        }
                    }
                }
            } catch (e: Exception) {      // folder not readable → skip it, but report it
                errors++
                if (firstError == null) firstError = "${e.javaClass.simpleName}: ${e.message}"
            }
            dirs++
            if (dirs % 20 == 0) progress("Scanning $rootName… ${found.size} files")
        }
        if (stop()) return Result(found.size, dirs, errors, firstError, rootName)
        progress("Updating index… ${found.size} files")
        save(treeUri.toString(), found)
        return Result(found.size, dirs, errors, firstError, rootName)
    }

    private fun save(tree: String, found: List<Found>) {
        val w = db.writableDatabase
        w.beginTransaction()
        try {
            w.execSQL("UPDATE docs SET seen=0 WHERE tree=?", arrayOf(tree))
            val known = HashMap<String, Pair<Long, Long>>()     // uri → (size, mtime)
            w.rawQuery("SELECT uri, size, mtime FROM docs WHERE tree=?", arrayOf(tree)).use { c ->
                while (c.moveToNext()) known[c.getString(0)] = Pair(c.getLong(1), c.getLong(2))
            }
            val ins = w.compileStatement(
                "INSERT INTO docs(uri, tree, relpath, name, lname, ext, size, mtime, dno, rev, onpad, seen) " +
                    "VALUES (?,?,?,?,?,?,?,?,?,?,1,1)"
            )
            val upd = w.compileStatement(
                "UPDATE docs SET relpath=?, name=?, lname=?, ext=?, size=?, mtime=?, seen=1, readst=0 WHERE uri=?"
            )
            val seen = w.compileStatement("UPDATE docs SET seen=1 WHERE uri=?")
            for (f in found) {
                val k = known[f.uri]
                when {
                    k == null -> {
                        val (dno, rev) = Names.dnoRev(f.name)
                        ins.clearBindings()
                        ins.bindString(1, f.uri)
                        ins.bindString(2, tree)
                        ins.bindString(3, f.relpath)
                        ins.bindString(4, f.name)
                        ins.bindString(5, f.name.lowercase(Locale.ROOT))
                        ins.bindString(6, Names.ext(f.name))
                        ins.bindLong(7, f.size)
                        ins.bindLong(8, f.mtime)
                        if (dno != null) ins.bindString(9, dno) else ins.bindNull(9)
                        if (rev != null) ins.bindString(10, rev) else ins.bindNull(10)
                        ins.executeInsert()
                    }
                    k.first != f.size || k.second != f.mtime -> {
                        upd.clearBindings()
                        upd.bindString(1, f.relpath)
                        upd.bindString(2, f.name)
                        upd.bindString(3, f.name.lowercase(Locale.ROOT))
                        upd.bindString(4, Names.ext(f.name))
                        upd.bindLong(5, f.size)
                        upd.bindLong(6, f.mtime)
                        upd.bindString(7, f.uri)
                        upd.executeUpdateDelete()
                    }
                    else -> {
                        seen.clearBindings()
                        seen.bindString(1, f.uri)
                        seen.executeUpdateDelete()
                    }
                }
            }
            w.execSQL("DELETE FROM docs WHERE tree=? AND seen=0 AND onpad=1", arrayOf(tree))
            db.mergeLaptopRows(w)
            w.setTransactionSuccessful()
        } finally {
            w.endTransaction()
        }
    }

    fun removeTree(tree: String) {
        db.writableDatabase.execSQL("DELETE FROM docs WHERE tree=?", arrayOf(tree))
    }
}
