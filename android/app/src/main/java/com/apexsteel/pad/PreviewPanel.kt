package com.apexsteel.pad

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.view.View
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import java.util.concurrent.Executors

/** Right-hand (landscape) / lower (portrait) panel: preview of the selected document before opening it.
 *  PDF pages are drawn by Android's PdfRenderer (page ◀ ▶, zoom − +); photos are shown directly. */
class PreviewPanel(
    private val root: View,
    private val resolver: ContentResolver,
    private val onOpen: (Doc) -> Unit,
    private val onShare: (Doc) -> Unit,
    private val onCopy: (String) -> Unit,
) {
    private val name: TextView = root.findViewById(R.id.pvName)
    private val badges: TextView = root.findViewById(R.id.pvBadges)
    private val frame: FrameLayout = root.findViewById(R.id.pvFrame)
    private val image: ImageView = root.findViewById(R.id.pvImage)
    private val empty: TextView = root.findViewById(R.id.pvEmpty)
    private val pageText: TextView = root.findViewById(R.id.pvPage)
    private val prev: Button = root.findViewById(R.id.pvPrev)
    private val next: Button = root.findViewById(R.id.pvNext)
    private val zoomOut: Button = root.findViewById(R.id.pvZoomOut)
    private val zoomIn: Button = root.findViewById(R.id.pvZoomIn)
    private val info: TextView = root.findViewById(R.id.pvInfo)
    private val open: Button = root.findViewById(R.id.pvOpen)
    private val share: Button = root.findViewById(R.id.pvShare)
    private val copy: Button = root.findViewById(R.id.pvCopy)

    private val exec = Executors.newSingleThreadExecutor()     // PdfRenderer is used from this thread only
    private val main = Handler(Looper.getMainLooper())
    private var renderer: PdfRenderer? = null
    private var pfd: ParcelFileDescriptor? = null
    private var rendererUri: String? = null
    @Volatile private var job = 0

    var doc: Doc? = null
        private set
    private var page = 0
    private var pages = 1
    private var zoom = 1f

    init {
        prev.setOnClickListener { if (page > 0) { page--; render() } }
        next.setOnClickListener { if (page < pages - 1) { page++; render() } }
        zoomIn.setOnClickListener { if (zoom < 3f) { zoom += 0.5f; render() } }
        zoomOut.setOnClickListener { if (zoom > 1f) { zoom -= 0.5f; render() } }
        open.setOnClickListener { doc?.let(onOpen) }
        share.setOnClickListener { doc?.let(onShare) }
        copy.setOnClickListener { doc?.let { onCopy(it.name) } }
        clear()
    }

    fun clear() {
        doc = null
        name.text = ""
        badges.text = ""
        info.text = ""
        image.setImageDrawable(null)
        image.visibility = View.GONE
        empty.visibility = View.VISIBLE
        empty.text = root.context.getString(R.string.preview_hint)
        setNav(false)
        setActions(false)
    }

    fun show(d: Doc) {
        if (doc?.id != d.id) {
            page = 0
            zoom = 1f
        }
        doc = d
        name.text = d.name
        val b = ArrayList<String>()
        b.add(Names.typeLabel(d.ext, d.dtype))
        if (!d.rev.isNullOrBlank()) b.add("Rev ${d.rev}")
        if (!d.onPad) b.add("💻 only on laptop")
        badges.text = b.joinToString("  ·  ")
        val lines = ArrayList<String>()
        if (!d.dno.isNullOrBlank()) lines.add("Number: ${d.dno}")
        if (!d.title.isNullOrBlank()) lines.add("Title: ${d.title}")
        lines.add("Path: ${d.relpath}")
        if (!d.summary.isNullOrBlank()) lines.add("Summary: ${d.summary}")
        else if (!d.body.isNullOrBlank()) lines.add("Text: " + d.body.replace(Regex("\\s+"), " ").take(300) + "…")
        info.text = lines.joinToString("\n")
        setActions(d.onPad && d.uri != null)
        render()
    }

    private fun setNav(on: Boolean) {
        val v = if (on) View.VISIBLE else View.GONE
        prev.visibility = v
        next.visibility = v
        pageText.visibility = v
        zoomIn.visibility = v
        zoomOut.visibility = v
    }

    private fun setActions(on: Boolean) {
        open.isEnabled = on
        share.isEnabled = on
        copy.isEnabled = doc != null
    }

    private fun message(t: String) {
        image.visibility = View.GONE
        empty.visibility = View.VISIBLE
        empty.text = t
    }

    private fun render() {
        val d = doc ?: return
        val my = ++job
        if (!d.onPad || d.uri == null) {
            setNav(false)
            message("No preview: this document is only on the laptop.\n\n${d.relpath}")
            return
        }
        val isPdf = d.ext == "pdf"
        val isImage = d.ext in setOf("jpg", "jpeg", "png", "bmp", "webp", "heic")
        if (!isPdf && !isImage) {
            setNav(false)
            message("No preview for .${d.ext} files.\nTap OPEN to view it.")
            return
        }
        message("Loading preview…")
        val target = ((if (frame.width > 0) frame.width else 1200) * zoom).toInt().coerceIn(400, 3000)
        exec.execute {
            try {
                val bmp: Bitmap? = if (isPdf) renderPdf(d.uri, target) else decodeImage(Uri.parse(d.uri), target)
                main.post {
                    if (my != job) return@post
                    if (bmp == null) {
                        message("Cannot preview this file.\nTap OPEN to view it.")
                    } else {
                        image.setImageBitmap(bmp)
                        image.visibility = View.VISIBLE
                        empty.visibility = View.GONE
                    }
                    setNav(isPdf)
                    pageText.text = if (isPdf) "${page + 1} / $pages" else ""
                    prev.isEnabled = page > 0
                    next.isEnabled = page < pages - 1
                    zoomOut.isEnabled = zoom > 1f
                    zoomIn.isEnabled = zoom < 3f
                    if (!isPdf) setNav(false)
                }
            } catch (e: Throwable) {
                main.post { if (my == job) message("Cannot preview this file (${e.javaClass.simpleName}).\nTap OPEN to view it.") }
            }
        }
    }

    /** Runs on [exec]. Keeps the renderer open while the same document is shown. */
    private fun renderPdf(uri: String, width: Int): Bitmap? {
        if (rendererUri != uri) {
            closeRenderer()
            val fd = resolver.openFileDescriptor(Uri.parse(uri), "r") ?: return null
            pfd = fd
            renderer = PdfRenderer(fd)
            rendererUri = uri
        }
        val r = renderer ?: return null
        pages = r.pageCount
        if (pages == 0) return null
        if (page >= pages) page = pages - 1
        val p = r.openPage(page)
        try {
            val h = (width.toLong() * p.height / maxOf(1, p.width)).toInt().coerceIn(1, 4000)
            val bmp = Bitmap.createBitmap(width, h, Bitmap.Config.ARGB_8888)
            bmp.eraseColor(Color.WHITE)
            p.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
            return bmp
        } finally {
            p.close()
        }
    }

    private fun decodeImage(uri: Uri, width: Int): Bitmap? {
        val o = BitmapFactory.Options()
        o.inJustDecodeBounds = true
        resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, o) }
        var sample = 1
        while (o.outWidth / (sample * 2) >= width) sample *= 2
        val o2 = BitmapFactory.Options()
        o2.inSampleSize = sample
        return resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, o2) }
    }

    private fun closeRenderer() {
        try {
            renderer?.close()
        } catch (e: Exception) {
        }
        try {
            pfd?.close()
        } catch (e: Exception) {
        }
        renderer = null
        pfd = null
        rendererUri = null
    }

    fun release() {
        exec.execute { closeRenderer() }
        exec.shutdown()
    }
}
