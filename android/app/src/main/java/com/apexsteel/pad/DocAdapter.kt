package com.apexsteel.pad

import android.graphics.Color
import android.text.SpannableString
import android.text.Spanned
import android.text.style.BackgroundColorSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import java.text.DateFormat
import java.util.Date
import java.util.Locale

class DocAdapter(
    private val onOpen: (Doc) -> Unit,
    private val onLong: (Doc) -> Unit,
) : RecyclerView.Adapter<DocAdapter.VH>() {

    private var items: List<Doc> = emptyList()
    var selectedId: Long = -1
        set(v) {
            field = v
            notifyDataSetChanged()
        }
    private var terms: List<String> = emptyList()

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val name: TextView = v.findViewById(R.id.name)
        val badges: TextView = v.findViewById(R.id.badges)
        val path: TextView = v.findViewById(R.id.path)
        val snippet: TextView = v.findViewById(R.id.snippet)
    }

    fun submit(list: List<Doc>, query: String) {
        items = list
        val ex = Synonyms.expand(query)
        terms = ex.rest.split(Regex("""[^\p{L}\p{N}]+""")).filter { it.length >= 2 } +
            ex.groups.flatten().filter { it.length >= 3 }.sortedByDescending { it.length }
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH =
        VH(LayoutInflater.from(parent.context).inflate(R.layout.item_doc, parent, false))

    override fun getItemCount() = items.size

    override fun onBindViewHolder(h: VH, position: Int) {
        val d = items[position]
        h.name.text = highlight(d.name)
        val b = ArrayList<String>()
        b.add(Names.typeLabel(d.ext, d.dtype))
        if (!d.rev.isNullOrBlank()) b.add("Rev ${d.rev}")
        if (d.size > 0) b.add(sizeText(d.size))
        if (d.mtime > 0) b.add(DateFormat.getDateInstance(DateFormat.MEDIUM).format(Date(d.mtime)))
        if (!d.onPad) b.add("💻 only on laptop")
        h.badges.text = b.joinToString("  ·  ")
        h.path.text = d.relpath
        val snip = snippet(d)
        h.snippet.visibility = if (snip.isEmpty()) View.GONE else View.VISIBLE
        h.snippet.text = highlight(snip)
        h.itemView.alpha = if (d.onPad) 1f else 0.6f
        h.itemView.setBackgroundResource(if (d.id == selectedId) R.drawable.card_selected else R.drawable.card)
        h.itemView.setOnClickListener { onOpen(d) }
        h.itemView.setOnLongClickListener { onLong(d); true }
    }

    private fun snippet(d: Doc): String {
        val body = d.body ?: ""
        val low = body.lowercase(Locale.ROOT)
        for (t in terms) {
            val i = low.indexOf(t)
            if (i >= 0) {
                val a = maxOf(0, i - 60)
                val e = minOf(body.length, i + 140)
                return (if (a > 0) "…" else "") + body.substring(a, e).replace(Regex("\\s+"), " ") + "…"
            }
        }
        if (!d.title.isNullOrBlank() && d.title != d.name) {
            return d.title + (if (!d.summary.isNullOrBlank()) " — " + d.summary else "")
        }
        return d.summary ?: ""
    }

    private fun highlight(s: String): CharSequence {
        if (terms.isEmpty() || s.isEmpty()) return s
        val sp = SpannableString(s)
        val low = s.lowercase(Locale.ROOT)
        for (t in terms) {
            var i = low.indexOf(t)
            while (i >= 0) {
                sp.setSpan(BackgroundColorSpan(Color.parseColor("#FFE08A")), i, i + t.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                i = low.indexOf(t, i + t.length)
            }
        }
        return sp
    }

    private fun sizeText(b: Long): String = when {
        b >= 1_000_000 -> String.format(Locale.ROOT, "%.1f MB", b / 1e6)
        b >= 1_000 -> String.format(Locale.ROOT, "%d kB", b / 1000)
        else -> "$b B"
    }
}
