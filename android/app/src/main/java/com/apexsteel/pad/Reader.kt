package com.apexsteel.pad

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import java.util.zip.ZipInputStream

/** 📖 Reads the text inside documents on the pad: PDF (text layer, e.g. CAD title blocks), Word .docx,
 *  Excel .xlsx, text / csv. Scanned PDFs without text give nothing (OCR is not included). */
class Reader(context: Context, private val resolver: ContentResolver) {

    init {
        PDFBoxResourceLoader.init(context.applicationContext)
    }

    companion object {
        val READABLE = setOf("pdf", "docx", "xlsx", "xlsm", "txt", "csv", "log", "md")
        const val MAX_CHARS = 20_000
        const val MAX_PDF_BYTES = 60_000_000L
        const val MAX_PDF_PAGES = 20
    }

    /** Returns the text (possibly empty). Throws on unreadable files. */
    fun read(uri: Uri, ext: String, size: Long): String = when (ext) {
        "pdf" -> if (size > MAX_PDF_BYTES) "" else pdf(uri)
        "docx" -> zipXml(uri, "word/document.xml")
        "xlsx", "xlsm" -> zipXml(uri, "xl/sharedStrings.xml")
        else -> plain(uri)
    }

    private fun pdf(uri: Uri): String {
        resolver.openInputStream(uri)?.use { input ->
            PDDocument.load(input).use { doc ->
                val st = PDFTextStripper()
                st.startPage = 1
                st.endPage = minOf(doc.numberOfPages, MAX_PDF_PAGES)
                return clean(st.getText(doc))
            }
        }
        return ""
    }

    private fun zipXml(uri: Uri, entry: String): String {
        resolver.openInputStream(uri)?.use { input ->
            ZipInputStream(input).use { zip ->
                var e = zip.nextEntry
                while (e != null) {
                    if (e.name == entry) {
                        val xml = zip.readBytes().toString(Charsets.UTF_8)
                        val txt = xml.replace(Regex("</w:p>|</si>|<w:br/>|<w:tab/>"), "\n")
                            .replace(Regex("<[^>]+>"), "")
                            .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"")
                            .replace("&apos;", "'")
                        return clean(txt)
                    }
                    e = zip.nextEntry
                }
            }
        }
        return ""
    }

    private fun plain(uri: Uri): String {
        resolver.openInputStream(uri)?.use { input ->
            val buf = ByteArray(200_000)
            val n = input.read(buf)
            if (n > 0) return clean(String(buf, 0, n, Charsets.UTF_8))
        }
        return ""
    }

    private fun clean(s: String): String =
        s.replace(Regex("[ \\t\\x0B\\f\\r]+"), " ").replace(Regex("\\n\\s*\\n+"), "\n").trim().take(MAX_CHARS)
}
