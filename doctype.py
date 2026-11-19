"""Recognises the type of a drawing: mechanical, hydraulic schematic, P&ID, electrical schematic."""
import re

LABELS = {"mechanical": "Mechanical drawing", "hydraulic": "Hydraulic schematic", "pid": "P&ID (process)",
          "electrical": "Electrical schematic", "drawing": "Drawing (other)", "document": "Document",
          "sheet": "Spreadsheet", "photo": "Photo", "email": "Email", "slides": "Presentation", "text": "Text"}

_P = lambda *ps: [re.compile(p, re.I) for p in ps]

PATTERNS = {
    "mechanical": _P(r"\bsection\s+[a-z]\s*-\s*[a-z]\b", r"\bdetail\s+[a-z]\b", r"\bscale\s*:?\s*1\s*:\s*\d+",
                     r"±\s*\d", r"\bISO\s*2768\b", r"\bRa\s*\d", r"\bgeneral\s+tolerances?\b", r"Ø\s*\d",
                     r"\bchamfer", r"\bweld(ing|ed)?\b", r"\bpart\s*(no|list|number)\b", r"\bqty\b",
                     r"\bweight\b", r"\bmaterial\b", r"\b(H|h)7\b|\bg6\b|\bk6\b", r"\bthread\b|\bM\d{1,2}x\d",
                     r"比例|材料|重量|技术要求|剖面|公差|焊接"),
    "hydraulic": _P(r"\d\s*bar\b", r"l/min", r"\bcm[³3]\b", r"\bhydraul", r"\baccumulator", r"\bpump\b",
                    r"\bservo\s*valve|\bproportional\s*valve", r"\brelief\s*valve|\bpressure\s*relief",
                    r"\bISO\s*1219\b", r"\bHPU\b|\bpower\s*unit\b", r"\btank\b|\breservoir\b",
                    r"\b(Y|S)\d{1,3}[A-Z]?\b", r"\bcylinder\b", r"\bfilter\b", r"\bcheck\s*valve|\bpilot",
                    r"液压|油缸|蓄能器|溢流阀|泵站|换向阀"),
    "pid": _P(r"\b(PT|TT|FT|LT|PI|TI|FI|LI|PIC|TIC|FIC|LIC|PCV|TCV|FCV|LCV|FV|XV|HV|PSV|PSH|PSL|TSH|LSH)[-_ ]?\d{2,5}[A-Z]?\b",
              r"\b\d{1,2}\"?-[A-Z]{1,4}-\d{2,5}", r"\bDN\s?\d{2,4}\b", r"\bPN\s?\d{1,3}\b", r"\bP\s?&\s?ID\b",
              r"\bpiping\s+(and|&)\s+instrument", r"\binstrument", r"\bline\s*(no|number)\b", r"\bcontrol\s*valve",
              r"\bnitrogen|\boxygen|\bcooling\s*water|\bsteam\b|\bcompressed\s*air", r"管道|仪表|阀门|工艺流程"),
    "electrical": _P(r"\b\d{3}\s?V\s?AC\b|\bVAC\b", r"\b24\s?V\s?DC\b|\bVDC\b", r"\bterminal", r"\bMCC\b",
                     r"\bcontactor", r"\bPLC\b|\bI/O\b", r"\b-?[QFK]\d{1,3}\b", r"\bX\d{1,3}:\d{1,3}\b",
                     r"\bwire|\bcable\b", r"mm²|mm2\b", r"\bcircuit\s*breaker|\bfuse\b", r"\bmotor\s*starter|\bVFD\b|\binverter",
                     r"电气|接线|端子|断路器|电缆"),
}


def scores(text: str) -> dict:
    sample = (text or "")[:60_000]
    out = {}
    for k, pats in PATTERNS.items():
        s = 0
        for p in pats:
            n = len(p.findall(sample))
            s += min(n, 6) ** 0.5 if n else 0   # many hits of one pattern count less than many patterns
        out[k] = round(s, 2)
    return out


def classify(name: str, ext: str, kind: str, text: str, large_format: bool = False) -> str:
    if kind in ("photo", "email", "sheet", "slides", "text"):
        return kind
    if ext in ("dxf", "dwg") or kind in ("drawing", "pdf", "scan", "doc"):
        sc = scores((name or "") + "\n" + (text or ""))
        best = max(sc, key=sc.get)
        ordered = sorted(sc.values(), reverse=True)
        drawingish = ext in ("dxf", "dwg") or kind == "drawing" or large_format
        need = 2.0 if drawingish else 5.0          # plain documents need much stronger evidence
        if ordered[0] >= need and ordered[0] >= 1.3 * ordered[1]:
            return best
        return "drawing" if drawingish else "document"
    return "document"
