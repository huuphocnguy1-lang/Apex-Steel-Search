"""OCR: reads text in photos and scanned pages (Chinese + English/Latin) with RapidOCR, fully offline."""
import logging
import threading

_engine = None
_error = None
_lock = threading.Lock()
log = logging.getLogger(__name__)


def _get():
    global _engine, _error
    if _engine is not None or _error is not None:
        return _engine
    with _lock:
        if _engine is None and _error is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                _engine = RapidOCR()
            except Exception as e:  # not installed / model problem
                _error = str(e)
                log.warning("OCR not available: %s", e)
    return _engine


def available() -> bool:
    return _get() is not None


def error() -> str | None:
    _get()
    return _error


def image_to_text(img, min_score: float = 0.5, max_side: int = 2200) -> str:
    """img: PIL.Image. Returns recognised text, one line per text box."""
    eng = _get()
    if eng is None:
        return ""
    import numpy as np
    img = img.convert("RGB")
    w, h = img.size
    m = max(w, h)
    if m > max_side:
        s = max_side / m
        img = img.resize((max(1, int(w * s)), max(1, int(h * s))))
    arr = np.ascontiguousarray(np.array(img)[:, :, ::-1])  # RGB -> BGR
    with _lock:  # the ONNX session is shared
        result, _ = eng(arr)
    if not result:
        return ""
    lines = []
    for r in result:
        try:
            if float(r[2]) >= min_score:
                lines.append(str(r[1]))
        except (IndexError, ValueError, TypeError):
            continue
    return "\n".join(lines)
