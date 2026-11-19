"""Hydraulics: calculators, component tags in schematics, AI explanation of a selected zone of a PDF schematic."""
import base64
import math
import re

ISO_TARGETS = [("Servo valves", "16/14/11 or cleaner"), ("Proportional valves", "17/15/12"),
               ("Piston pumps, directional valves", "18/16/13"), ("Gear pumps, cylinders", "19/17/14")]


# ------------------------------------------------------------------ calculators
def cylinder(bore_mm, rod_mm, pressure_bar, flow_lmin):
    ap = math.pi / 4 * (bore_mm / 1000) ** 2
    aa = math.pi / 4 * ((bore_mm / 1000) ** 2 - (rod_mm / 1000) ** 2)
    p = pressure_bar * 1e5
    q = flow_lmin / 60000
    return {"push_kN": p * ap / 1000, "pull_kN": p * aa / 1000,
            "v_ext_mm_s": q / ap * 1000 if ap else 0, "v_ret_mm_s": q / aa * 1000 if aa > 0 else 0,
            "area_ratio": ap / aa if aa > 0 else 0}


def pump(disp_cm3, rpm, pressure_bar, eff_vol=0.95, eff_tot=0.85):
    q = disp_cm3 * rpm * eff_vol / 1000
    return {"flow_lmin": q, "power_kW": pressure_bar * q / (600 * eff_tot) if eff_tot else 0}


def accumulator(size_l, precharge_bar, p_min_bar, p_max_bar, n=1.4):
    """Usable volume between p_min and p_max (gauge pressures in bar), polytropic gas law."""
    p0, p1, p2 = precharge_bar + 1, p_min_bar + 1, p_max_bar + 1
    if not (p0 < p1 < p2):
        return {"usable_l": 0.0, "warning": "Need pre-charge < minimum pressure < maximum pressure"}
    dv = size_l * p0 ** (1 / n) * (p1 ** (-1 / n) - p2 ** (-1 / n))
    warn = "Pre-charge is usually 0.8–0.9 × minimum working pressure" if precharge_bar < 0.6 * p_min_bar else ""
    return {"usable_l": dv, "warning": warn}


# ------------------------------------------------------------------ tags in schematics
TAG_RE = re.compile(r"\b(SV|PV|DBV|DRV|RV|CV|PT|PS|PI|TT|TS|LT|LS|ST|ACC|CYL|HX|WT|MP|P|M|Y|S|F|C|Z|V|A)[-.]?(\d{1,3}[A-Z]?)\b")
PREFIX = {
    "SV": "servo valve", "PV": "proportional valve", "DBV": "pressure relief valve", "DRV": "pressure reducing valve",
    "RV": "relief / check valve", "CV": "check valve", "PT": "pressure transmitter", "PS": "pressure switch",
    "PI": "pressure gauge", "TT": "temperature transmitter", "TS": "temperature switch", "LT": "level / position transmitter",
    "LS": "level / limit switch", "ST": "position sensor", "ACC": "accumulator", "CYL": "cylinder", "HX": "heat exchanger",
    "WT": "cooler", "MP": "motor-pump unit", "P": "pump", "M": "motor", "Y": "solenoid coil", "S": "switch / sensor",
    "F": "filter", "C": "cylinder", "Z": "cylinder", "V": "valve", "A": "accumulator / actuator",
}
VALUE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(bar|l/min|L/min|cm³|cm3|l\b|°C|µm|um|kW|rpm|mm)", re.I)


def describe_tag(tag: str) -> str:
    m = TAG_RE.match(tag)
    return PREFIX.get(m.group(1), "component") if m else "component"


def components_from_words(words) -> list:
    """words: PyMuPDF page.get_text('words') tuples (x0,y0,x1,y1,word,...). Returns tags with nearby values."""
    found = {}
    vals = [(w[0], w[1], w[4] + " " + (words[i + 1][4] if i + 1 < len(words) else "")) for i, w in enumerate(words)]
    for w in words:
        m = TAG_RE.fullmatch(w[4].strip(",;:()"))
        if not m:
            continue
        tag = m.group(1) + m.group(2)
        if m.group(1) in ("S", "Q") and m.group(2)[:3].isdigit() and int(m.group(2)[:3]) >= 200:
            continue  # steel grade (S355), not a switch
        if tag in found:
            continue
        near = []
        for x, y, txt in vals:
            if abs(x - w[0]) < 90 and abs(y - w[1]) < 40:
                for vm in VALUE_RE.finditer(txt):
                    s = f"{vm.group(1)} {vm.group(2)}"
                    if s not in near:
                        near.append(s)
        found[tag] = {"tag": tag, "type": PREFIX.get(m.group(1), "component"), "values": near[:3],
                      "x": w[0], "y": w[1]}
    return sorted(found.values(), key=lambda c: (c["type"], c["tag"]))


def components_from_text(text: str) -> list:
    out = {}
    for m in TAG_RE.finditer(text or ""):
        tag = m.group(1) + m.group(2)
        out.setdefault(tag, {"tag": tag, "type": PREFIX.get(m.group(1), "component"), "values": []})
    return sorted(out.values(), key=lambda c: (c["type"], c["tag"]))


# ------------------------------------------------------------------ PDF zone
def page_count(pdf_path: str) -> int:
    import fitz
    with fitz.open(pdf_path) as d:
        return d.page_count


def page_components(pdf_path: str, page_no: int) -> list:
    import fitz
    with fitz.open(pdf_path) as d:
        return components_from_words(d[page_no].get_text("words"))


def zone_data(pdf_path: str, page_no: int, rect_pt, dpi: int = 160) -> dict:
    """rect_pt = (x0, y0, x1, y1) in PDF points. Returns text, tags, values and a JPEG image of the zone."""
    import fitz
    with fitz.open(pdf_path) as d:
        page = d[page_no]
        r = fitz.Rect(*rect_pt) & page.rect
        words = [w for w in page.get_text("words") if fitz.Rect(w[:4]).intersects(r)]
        text = page.get_text("text", clip=r)
        pix = page.get_pixmap(clip=r, dpi=dpi, alpha=False)
        if pix.width * pix.height > 2400 * 2400:
            pix = page.get_pixmap(clip=r, dpi=max(60, int(dpi * 2400 / max(pix.width, pix.height))), alpha=False)
        img = base64.b64encode(pix.tobytes("jpeg")).decode()
        full = page.get_text("text")
    return {"text": text, "components": components_from_words(words), "values": VALUE_RE.findall(text),
            "image": img, "page_text": full}


HYD_SYSTEM = ("You are a senior industrial hydraulics engineer. You read hydraulic schematics drawn to ISO 1219. "
              "You receive an image of a ZONE selected by the user, the text found in that zone, and the component tags. "
              "Explain: 1) the components you recognise (symbol + tag + setting), 2) the function of this zone in the "
              "circuit and the oil flow path, 3) what happens when the relevant solenoids are energised / de-energised, "
              "4) typical faults of this zone and what to check, 5) safety notes. If a symbol or connection is unclear, "
              "say so instead of guessing. Answer in the user's language, concise, with headings.")


def local_zone_explanation(z: dict) -> str:
    if not z["components"]:
        return ("No component tag found as text in this zone (the drawing may be scanned or tags are graphics). "
                "Start the AI picture model to analyse the image of the zone.")
    lines = ["**Components found in the zone (from the PDF text):**"]
    for c in z["components"]:
        lines.append(f"- **{c['tag']}** — {c['type']}" + (f" ({', '.join(c['values'])})" if c["values"] else ""))
    lines.append("\nStart the AI engine (Settings) for a full explanation of the function, flow path and faults.")
    return "\n".join(lines)


def explain_zone(db, ai, pdf_path: str, page_no: int, rect_pt, question: str = "") -> dict:
    z = zone_data(pdf_path, page_no, rect_pt)
    comp = "\n".join(f"- {c['tag']}: {c['type']} {', '.join(c['values'])}" for c in z["components"]) or "(none as text)"
    user = (f"TEXT IN ZONE:\n{z['text'][:3000]}\n\nCOMPONENT TAGS:\n{comp}\n\n"
            f"OTHER TEXT ON THE PAGE (context):\n{z['page_text'][:2500]}\n\n"
            f"QUESTION: {question or 'Explain this zone of the hydraulic schematic.'}")
    try:
        text = ai.chat([{"role": "system", "content": HYD_SYSTEM}, {"role": "user", "content": user}], images=[z["image"]])
        ok = True
    except Exception as e:
        text = local_zone_explanation(z) + f"\n\n_AI not available: {e}_"
        ok = False
    return {"text": text, "components": z["components"], "ai": ok}
