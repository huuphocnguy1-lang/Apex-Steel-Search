package com.apexsteel.pad

import java.util.Locale

/** ESP / steel / hydraulics synonyms (English, abbreviations, Chinese). Typing any word of a group also finds the
 *  others. Multi-word English entries match in any order ("shear rotary" = "rotary shear"). */
object Synonyms {
    val GROUPS: List<List<String>> = listOf(
        listOf("rotary shear", "crop shear", "drum shear", "shr", "转鼓剪", "转鼓飞剪", "切头剪", "飞剪"),
        listOf("pendulum shear", "pendular shear", "ps", "shp", "摆式剪", "摆剪"),
        listOf("high speed shear", "flying shear", "hss", "高速飞剪"),
        listOf("hgc", "hydraulic gap control", "agc cylinder", "液压压下", "压下"),
        listOf("looper", "活套"),
        listOf("down coiler", "coiler", "卷取机", "卷曲机"),
        listOf("wrapper roll", "助卷辊"),
        listOf("mandrel", "卷筒"),
        listOf("induction heater", "idh", "inductor", "感应加热"),
        listOf("descaler", "descaling", "dsc", "除鳞"),
        listOf("hydraulic", "hyd", "液压"),
        listOf("accumulator", "蓄能器"),
        listOf("servo valve", "伺服阀"),
        listOf("schematic", "原理图"),
        listOf("roughing mill", "high reduction mill", "hrm", "rm", "粗轧"),
        listOf("finishing mill", "fm", "精轧"),
        listOf("caster", "ccm", "continuous casting", "连铸"),
        listOf("mould", "mold", "结晶器"),
        listOf("laminar cooling", "lcs", "层流冷却"),
        listOf("pinch roll", "夹送辊"),
        listOf("side guide", "侧导板"),
        listOf("general arrangement", "ga", "总图", "总装"),
        listOf("parts list", "bom", "明细"),
    )

    data class Expanded(val groups: List<List<String>>, val rest: String)

    fun expand(query: String): Expanded {
        var q = " " + query.lowercase(Locale.ROOT).replace(Regex("""[^\p{L}\p{N}]+"""), " ") + " "
        val groups = ArrayList<List<String>>()
        val cand = GROUPS.flatMap { g -> g.map { w -> Pair(w, g) } }.sortedByDescending { it.first.length }
        for ((w, g) in cand) {
            if (w.all { it.code < 128 }) {
                val ws = w.split(' ')
                if (ws.all { q.contains(" $it ") }) {
                    if (g !in groups) groups.add(g)
                    for (x in ws) q = q.replaceFirst(" $x ", " ")
                }
            } else if (q.contains(w)) {
                if (g !in groups) groups.add(g)
                q = q.replaceFirst(w, " ")
            }
        }
        return Expanded(groups, q.trim())
    }

    /** Short ASCII words (ps, shr, rm…) must match a whole word: use the FTS index for them. */
    fun isShortWord(w: String) = w.length <= 3 && w.all { it.code < 128 && it.isLetterOrDigit() }
}
