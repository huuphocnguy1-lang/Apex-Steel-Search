"""Text extraction for every supported file type. Missing optional libraries never crash: the file is
still indexed by name, with a note in `error`."""
import email
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from email import policy

from . import ocr

log = logging.getLogger(__name__)

IMAGE_EXTS = {"jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp", "heic"}
KINDS = {
    "pdf": "pdf",
    "docx": "doc", "docm": "doc", "doc": "doc", "rtf": "doc", "odt": "doc",
    "txt": "text", "md": "text", "log": "text",
    "csv": "sheet", "xlsx": "sheet", "xlsm": "sheet", "xls": "sheet",
    "pptx": "slides",
    "msg": "email", "eml": "email",
    "dxf": "drawing", "dwg": "drawing",
    **{e: "photo" for e in IMAGE_EXTS},
}
SUPPORTED = set(KINDS)
MAX_CHARS = 400_000


@dataclass
class Extracted:
    text: str = ""
    pages: int = 0
    ocr: bool = False
    large_format: bool = False   # PDF page bigger than A3 landscape -> probably a drawing
    title: str = ""
    phash: str | None = None
    error: str | None = None


def extract(path: str, cfg: dict) -> Extracted:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    fn = {
        "pdf": _pdf, "docx": _docx, "docm": _docx, "pptx": _pptx,
        "xlsx": _xlsx, "xlsm": _xlsx, "csv": _textfile, "txt": _textfile, "md": _textfile, "log": _textfile,
        "msg": _msg, "eml": _eml, "dxf": _dxf, "dwg": _dwg, "rtf": _rtf, "odt": _odt,
    }.get(ext)
    if ext in IMAGE_EXTS:
        fn = _image
    if fn is None:
        return Extracted(error=f".{ext}: content not readable yet (indexed by file name)")
    try:
        r = fn(path, cfg)
    except Exception as e:
        log.exception("extract failed: %s", path)
        r = Extracted(error=f"{type(e).__name__}: {e}")
    if r.text and len(r.text) > MAX_CHARS:
        r.text = r.text[:MAX_CHARS]
    r.text = re.sub(r"[ \t\r\f\v]+", " ", r.text or "")
    r.text = re.sub(r"\n\s*\n+", "\n", r.text).strip()
    return r


# ---------------------------------------------------------------- formats
def _textfile(path, cfg):
    raw = open(path, "rb").read(MAX_CHARS * 2)
    for enc in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            return Extracted(text=raw.decode(enc))
        except UnicodeDecodeError:
            continue
    return Extracted(text=raw.decode("utf-8", "ignore"))


def _pdf(path, cfg):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return Extracted(error="PyMuPDF not installed")
    out, used_ocr, large = [], False, False
    ocr_left = int(cfg.get("ocr_max_pdf_pages", 30)) if cfg.get("ocr_enabled", True) else 0
    with fitz.open(path) as doc:
        n = doc.page_count
        title = (doc.metadata or {}).get("title") or ""
        for i, page in enumerate(doc):
            if i >= 500:
                break
            r = page.rect
            if max(r.width, r.height) > 1100:  # > A3 (1191 x 842 pt)
                large = True
            t = page.get_text("text") or ""
            if len(t.strip()) < 30 and ocr_left > 0 and ocr.available():
                from PIL import Image
                pix = page.get_pixmap(dpi=200 if max(r.width, r.height) < 1300 else 130, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                t = ocr.image_to_text(img)
                used_ocr = used_ocr or bool(t)
                ocr_left -= 1
            out.append(t)
    return Extracted(text="\n".join(out), pages=n, ocr=used_ocr, large_format=large, title=title)


def _docx(path, cfg):
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for table in d.tables:
        for row in table.rows:
            cells = []
            for c in row.cells:
                t = c.text.strip()
                if t and (not cells or cells[-1] != t):
                    cells.append(t)
            if cells:
                parts.append(" | ".join(cells))
    title = (d.core_properties.title or "").strip()
    return Extracted(text="\n".join(parts), title=title)


def _pptx(path, cfg):
    from pptx import Presentation
    prs = Presentation(path)
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        parts.append(f"[Slide {i}]")
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
                parts.append(shape.text_frame.text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
    return Extracted(text="\n".join(parts), pages=len(prs.slides))


def _xlsx(path, cfg):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts, size = [], 0
    try:
        for ws in wb.worksheets:
            parts.append(f"[Sheet {ws.title}]")
            for row in ws.iter_rows(values_only=True):
                vals = [str(v) for v in row if v is not None and str(v).strip()]
                if vals:
                    line = " | ".join(vals)
                    parts.append(line)
                    size += len(line)
                    if size > MAX_CHARS:
                        break
    finally:
        wb.close()
    return Extracted(text="\n".join(parts), pages=len(wb.sheetnames))


def _msg(path, cfg):
    try:
        import extract_msg
    except ImportError:
        return Extracted(error="extract-msg not installed")
    m = extract_msg.Message(path)
    try:
        text = f"From: {m.sender}\nTo: {m.to}\nDate: {m.date}\nSubject: {m.subject}\n\n{m.body or ''}"
        return Extracted(text=text, title=m.subject or "")
    finally:
        m.close()


def _eml(path, cfg):
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    body = msg.get_body(preferencelist=("plain", "html"))
    content = body.get_content() if body else ""
    if body is not None and body.get_content_type() == "text/html":
        content = re.sub(r"<[^>]+>", " ", content)
    text = f"From: {msg['from']}\nTo: {msg['to']}\nDate: {msg['date']}\nSubject: {msg['subject']}\n\n{content}"
    return Extracted(text=text, title=str(msg["subject"] or ""))


def _rtf(path, cfg):
    raw = open(path, "r", encoding="latin-1", errors="ignore").read()
    raw = re.sub(r"\\'[0-9a-f]{2}", "", raw)
    raw = re.sub(r"\\[a-z]+-?\d* ?|[{}]", " ", raw)
    return Extracted(text=raw)


def _odt(path, cfg):
    with zipfile.ZipFile(path) as z:
        xml = z.read("content.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</text:p>|<text:line-break/>", "\n", xml)
    return Extracted(text=re.sub(r"<[^>]+>", " ", xml))


def _image(path, cfg):
    from PIL import Image, ImageOps
    if path.lower().endswith(".heic"):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            return Extracted(error="HEIC needs pillow-heif")
    from .meta import dhash
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        ph = dhash(im)
        text = ocr.image_to_text(im) if cfg.get("ocr_enabled", True) else ""
    return Extracted(text=text, ocr=bool(text), phash=ph, pages=1)


def _dxf(path, cfg):
    try:
        from ezdxf import recover
    except ImportError:
        return Extracted(error="ezdxf not installed")
    doc, _auditor = recover.readfile(path)
    out, count = [], 0

    def take(entities):
        nonlocal count
        for e in entities:
            count += 1
            if count > 50_000:
                return
            t = e.dxftype()
            try:
                if t in ("TEXT", "ATTDEF"):
                    out.append(e.dxf.text)
                elif t == "MTEXT":
                    out.append(e.plain_text())
                elif t == "INSERT":
                    for a in e.attribs:  # title-block attributes
                        out.append(a.dxf.text)
                elif t == "DIMENSION":
                    s = e.dxf.get("text", "")
                    if s and s != "<>":
                        out.append(s)
            except Exception:
                continue

    for name in doc.layouts.names():
        take(doc.layouts.get(name))
    for block in doc.blocks:
        if not block.name.startswith("*"):
            take(block)
    seen, uniq = set(), []
    for t in out:
        t = (t or "").strip()
        if t and t not in seen:
            seen.add(t)
            uniq.append(t)
    return Extracted(text="\n".join(uniq), large_format=True)


def _dwg(path, cfg):
    oda = cfg.get("oda_path") or ""
    if not os.path.isfile(oda):
        return Extracted(error="DWG: install the free ODA File Converter and set its path in Settings")
    tmp = tempfile.mkdtemp(prefix="apexdwg_")
    try:
        ind, outd = os.path.join(tmp, "in"), os.path.join(tmp, "out")
        os.makedirs(ind)
        os.makedirs(outd)
        shutil.copy2(path, ind)
        flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        subprocess.run([oda, ind, outd, "ACAD2018", "DXF", "0", "1", "*.DWG"],
                       timeout=300, capture_output=True, creationflags=flags)
        for f in os.listdir(outd):
            if f.lower().endswith(".dxf"):
                return _dxf(os.path.join(outd, f), cfg)
        return Extracted(error="DWG conversion produced no DXF")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
