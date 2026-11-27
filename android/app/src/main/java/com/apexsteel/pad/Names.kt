package com.apexsteel.pad

import java.util.Locale

/** File-name helpers: revision, drawing-number key, file type. */
object Names {
    // _R00  -R1  " Rev B"  _REV_C  .rA   (token must be separated by _ - space or .)
    private val REV = Regex("""(?i)(?:^|[_\-\s.])(?:rev\.?[_\-\s]?|r)(\d{1,3}|[a-z]\d{0,2})(?=$|[_\-\s.])""")

    fun stem(name: String): String {
        val i = name.lastIndexOf('.')
        return if (i > 0) name.substring(0, i) else name
    }

    fun ext(name: String): String {
        val i = name.lastIndexOf('.')
        return if (i > 0 && i < name.length - 1) name.substring(i + 1).lowercase(Locale.ROOT) else ""
    }

    /** Returns (drawing-number key, revision) parsed from the file name. Key = name without the revision token. */
    fun dnoRev(name: String): Pair<String?, String?> {
        val s = stem(name)
        val m = REV.findAll(s).lastOrNull() ?: return Pair(null, null)
        val rev = m.groupValues[1].uppercase(Locale.ROOT)
        val key = (s.substring(0, m.range.first) + s.substring(m.range.last + 1)).trim('_', '-', ' ', '.')
        return Pair(if (key.length >= 4) key else null, rev)
    }

    /** Sort key so that A < B < C, 0 < 1 < 2, R00 < R01. */
    fun revKey(rev: String?): Pair<String, Int> {
        if (rev.isNullOrBlank()) return Pair("", -1)
        val m = Regex("""([A-Za-z]*)(\d*)""").find(rev.uppercase(Locale.ROOT)) ?: return Pair(rev, 0)
        return Pair(m.groupValues[1], m.groupValues[2].toIntOrNull() ?: 0)
    }

    fun compareRev(a: String?, b: String?): Int {
        val ka = revKey(a)
        val kb = revKey(b)
        val c = ka.first.compareTo(kb.first)
        return if (c != 0) c else ka.second.compareTo(kb.second)
    }

    val DRAWING_EXT = setOf("dwg", "dxf")
    val DRAWING_TYPES = setOf("mechanical", "hydraulic", "pid", "electrical", "drawing")
    val WORD = setOf("doc", "docx", "rtf", "odt")
    val EXCEL = setOf("xls", "xlsx", "xlsm", "csv", "ods")
    val PHOTO = setOf("jpg", "jpeg", "png", "heic", "bmp", "webp", "tif", "tiff")

    fun mime(ext: String): String = when (ext) {
        "pdf" -> "application/pdf"
        "doc" -> "application/msword"
        "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        "xls" -> "application/vnd.ms-excel"
        "xlsx", "xlsm" -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        "ppt" -> "application/vnd.ms-powerpoint"
        "pptx" -> "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        "csv" -> "text/csv"
        "txt", "log", "md" -> "text/plain"
        "jpg", "jpeg" -> "image/jpeg"
        "png" -> "image/png"
        "heic" -> "image/heic"
        "dwg" -> "image/vnd.dwg"
        "dxf" -> "image/vnd.dxf"
        else -> "*/*"
    }

    fun typeLabel(ext: String, dtype: String?): String = when {
        dtype == "hydraulic" -> "Hydraulic schematic"
        dtype == "mechanical" -> "Mechanical drawing"
        dtype == "electrical" -> "Electrical schematic"
        dtype == "pid" -> "P&ID"
        dtype == "drawing" || ext in DRAWING_EXT -> "Drawing"
        ext == "pdf" -> "PDF"
        ext in WORD -> "Word"
        ext in EXCEL -> "Excel"
        ext in PHOTO -> "Photo"
        ext.isEmpty() -> "File"
        else -> ext.uppercase(Locale.ROOT)
    }
}
