"""Automatic tags: drawing number, revision, project, steel grade, language, photo fingerprint."""
import os
import re

# "D-2401-S-101_RevC_Column bases.pdf" -> ("D-2401-S-101", "C");  "ABC-123 rev 02.dwg" -> ("ABC-123", "02")
_DNO_REV = re.compile(
    r"^([A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+){1,6}?)[-_. ]+(?:rev|r)[-_. ]?([A-Za-z]{1,2}\d{0,2}|\d{1,3})(?=[-_. ()\[\]]|$)",
    re.IGNORECASE)
_TEXT_DNO = re.compile(r"(?:DRAWING|DWG|DRG)\.?\s*(?:NO|NUMBER|N°|#)\.?\s*[:]?\s*([A-Z0-9][A-Z0-9\-_/.]{4,30})", re.I)
_TEXT_REV = re.compile(r"\bREV(?:ISION)?\.?\s*[:]?\s*([A-Z]{1,2}\d{0,2}|\d{1,2})\b")
_MATERIAL = re.compile(r"\b(S235|S275|S355|S420|S460|Q235|Q345|Q355|Q390|Q420)([A-Z0-9+]*)\b")
_CJK = re.compile(r"[一-鿿]")
_FR = re.compile(r"[éèêàçùœ]|\b(le|la|les|des|une|est|pour|avec|selon|dans)\b", re.I)


def drawing_number(name: str, text: str = "") -> tuple[str | None, str | None]:
    stem = os.path.splitext(name)[0]
    m = _DNO_REV.match(stem)
    if m and re.search(r"\d", m.group(1)):
        return m.group(1).upper().replace("_", "-"), m.group(2).upper()
    head = text[:6000]
    m = _TEXT_DNO.search(head)
    if m:
        r = _TEXT_REV.search(head)
        return m.group(1).upper().rstrip(".-_/"), (r.group(1).upper() if r else None)
    return None, None


def rev_key(rev: str | None):
    """Sort key: A < B < ... ; 0 < 1 < 2 ; P01 < P02."""
    if not rev:
        return ("", -1)
    m = re.match(r"([A-Z]*)(\d*)", rev.upper())
    return (m.group(1), int(m.group(2) or 0))


def material(text: str) -> str | None:
    grades = []
    for m in _MATERIAL.finditer(text[:200_000]):
        g = m.group(1) + m.group(2)
        if g not in grades:
            grades.append(g)
        if len(grades) >= 3:
            break
    return ", ".join(grades) or None


def language(text: str) -> str:
    sample = text[:20_000]
    if not sample.strip():
        return "—"
    cjk = len(_CJK.findall(sample))
    if cjk > 200 or cjk > len(re.sub(r"\s", "", sample)) * 0.15:
        return "中文"
    words = max(1, len(sample.split()))
    if len(_FR.findall(sample)) / words > 0.04:
        return "FR"
    return "EN"


def project(path: str, root: str | None, regex: str) -> str | None:
    try:
        m = re.search(regex, path, re.I)
        if m:
            return m.group(0).upper()
    except re.error:
        pass
    if root:
        rel = os.path.relpath(path, root)
        parts = rel.split(os.sep)
        if len(parts) > 1:
            return parts[0]
    return None


def title_from(name: str, text: str, given: str = "") -> str:
    if given and len(given) < 150:
        return given.strip()
    stem = os.path.splitext(name)[0]
    return re.sub(r"[_]+", " ", stem).strip()


def dhash(img, size: int = 8) -> str:
    """64-bit difference hash of a PIL image (for 'find similar photos')."""
    g = img.convert("L").resize((size + 1, size))
    px = list(g.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return f"{bits:016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def chunks(text: str, title: str, size: int = 900, overlap: int = 120, max_chunks: int = 12) -> list[str]:
    text = text.strip()
    if not text:
        return [title] if title else []
    out, i = [], 0
    while i < len(text) and len(out) < max_chunks:
        part = text[i:i + size]
        out.append(f"{title}\n{part}" if title else part)
        i += size - overlap
    return out
