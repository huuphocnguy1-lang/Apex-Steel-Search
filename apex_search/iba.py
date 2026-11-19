"""iba recordings: load signals exported from ibaAnalyzer (CSV / TXT), detect events, find the first signal that moved."""
import datetime
import os
import re
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Signal:
    name: str
    unit: str
    v: np.ndarray


@dataclass
class Recording:
    path: str
    t: np.ndarray
    signals: list = field(default_factory=list)
    t_label: str = "s"

    @property
    def name(self):
        return os.path.basename(self.path)


_NUM = re.compile(r"^[+-]?(\d+([.,]\d*)?|[.,]\d+)([eE][+-]?\d+)?$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}([.,]\d+)?$|^\d{1,2}:\d{2}:\d{2}([.,]\d+)?$")


def _num(x: str, dec_comma: bool):
    x = x.strip().strip('"')
    if dec_comma:
        x = x.replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return np.nan


def _ts(x: str):
    x = x.strip().strip('"').replace(",", ".")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%H:%M:%S.%f", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(x, fmt)
        except ValueError:
            continue
    return None


def load_csv(path: str, max_signals: int = 300) -> Recording:
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "gb18030", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 3:
        raise ValueError("File has fewer than 3 lines")
    sample = lines[min(len(lines) - 1, 20)]
    delim = ";" if ";" in sample else ("\t" if "\t" in sample else ",")
    dec_comma = delim != "," and re.search(r"\d,\d", sample) is not None
    rows = [l.split(delim) for l in lines]

    def is_data(r):
        if len(r) < 2:
            return False
        first = r[0].strip().strip('"').replace(",", ".")
        return (_NUM.match(first) or _TS.match(first)) and _NUM.match(r[1].strip().strip('"').replace(",", "."))

    start = next((i for i, r in enumerate(rows) if is_data(r)), None)
    if start is None:
        raise ValueError("No numeric data found (expected: time column + signal columns)")
    names = [c.strip().strip('"') for c in rows[start - 1]] if start >= 1 else []
    units = []
    if start >= 2 and all(len(c.strip()) <= 12 for c in rows[start - 1]) and len(rows[start - 2]) == len(rows[start - 1]):
        # two header rows: names + units
        cand_units = [c.strip().strip('"[]() ') for c in rows[start - 1]]
        if sum(bool(re.match(r"^[a-zA-Z°%/²³µ·\-]{0,8}$", u)) for u in cand_units) >= len(cand_units) * 0.7:
            names = [c.strip().strip('"') for c in rows[start - 2]]
            units = cand_units
    data = rows[start:]
    ncol = len(data[0])
    if not names or len(names) < ncol:
        names = (names + [f"Signal {i}" for i in range(len(names), ncol)])[:ncol]
    first = data[0][0].strip().strip('"')
    if _TS.match(first.replace(",", ".")) and not _NUM.match(first.replace(",", ".")):
        t0 = _ts(first)
        t = np.array([((_ts(r[0]) or t0) - t0).total_seconds() for r in data], dtype=float)
        t_label = f"s from {first}"
    else:
        t = np.array([_num(r[0], dec_comma) for r in data], dtype=float)
        t_label = names[0] if names[0] else "s"
    signals = []
    for j in range(1, min(ncol, max_signals + 1)):
        v = np.array([_num(r[j], dec_comma) if j < len(r) else np.nan for r in data], dtype=float)
        if np.all(np.isnan(v)):
            continue
        if np.any(np.isnan(v)):  # fill gaps
            idx = np.arange(len(v))
            ok = ~np.isnan(v)
            v = np.interp(idx, idx[ok], v[ok])
        nm = names[j] or f"Signal {j}"
        unit = units[j] if j < len(units) else ""
        m = re.match(r"^(.*?)\s*[\[(]([^\])]{1,10})[\])]\s*$", nm)   # "Speed [m/min]"
        if m and not unit:
            nm, unit = m.group(1).strip(), m.group(2)
        signals.append(Signal(nm, unit, v))
    if not signals:
        raise ValueError("No signal columns found")
    ok = ~np.isnan(t)
    if not np.all(ok):
        t = t[ok]
        for s in signals:
            s.v = s.v[ok]
    return Recording(path=path, t=t, signals=signals, t_label=t_label)


def load(path: str) -> Recording:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".dat":
        raise ValueError("iba .dat files: open them in ibaAnalyzer and use File → Export → ASCII/CSV, "
                         "then open the exported file here.")
    return load_csv(path)


# ------------------------------------------------------------------ event detection
def _rolling(v: np.ndarray, w: int):
    c1 = np.cumsum(np.insert(v, 0, 0.0))
    c2 = np.cumsum(np.insert(v * v, 0, 0.0))
    n = len(v)
    idx = np.arange(n)
    lo = np.maximum(0, idx - w + 1)
    cnt = idx - lo + 1
    s1 = c1[idx + 1] - c1[lo]
    s2 = c2[idx + 1] - c2[lo]
    mean = s1 / cnt
    var = np.maximum(0.0, s2 / cnt - mean * mean)
    return mean, np.sqrt(var)


def detect(t: np.ndarray, sig: Signal, t_from=None, t_to=None):
    """First abnormal change of a signal compared with its own start: step/spike, drift or oscillation."""
    v, tt = sig.v, t
    if t_from is not None:
        m = (t >= t_from) & (t <= t_to)
        v, tt = v[m], t[m]
    n = len(v)
    if n < 20:
        return None
    b = max(8, int(n * 0.15))
    base = v[:b]
    mean, sd = float(base.mean()), float(base.std()) or 1e-9
    rng = float(v.max() - v.min()) or 1.0
    w = max(6, n // 40)
    rm, rs = _rolling(v, w)
    d = np.abs(np.diff(v, prepend=v[0]))
    idx = np.arange(n)
    step = (idx >= b) & (d > max(10 * sd, 0.25 * rng))
    drift = (idx >= b) & (np.abs(rm - mean) > max(7 * sd, 0.015 * abs(mean) + 1e-9))
    osc = (idx >= b) & (rs > 4.5 * sd) & (rs > 0.04 * rng)
    cands = []
    if step.any():
        i = int(np.argmax(step))
        cands.append((i, "step / spike", "up" if v[i] > v[i - 1] else "down"))
    if drift.any():
        i = int(np.argmax(drift))
        cands.append((max(b, i - w // 3), "drift", "up" if rm[i] > mean else "down"))
    if osc.any():
        i = int(np.argmax(osc))
        win = v[max(0, i - w):i + 1]
        zc = int(np.sum(np.diff(np.sign(win - win.mean())) != 0))
        if zc >= 2:
            cands.append((max(b, i - w // 2), "oscillation", ""))
        else:
            cands.append((max(b, i - w // 2), "drift", "up" if win[-1] > win[0] else "down"))
    if not cands:
        return None
    i, typ, direction = min(cands, key=lambda c: c[0])
    return {"signal": sig.name, "unit": sig.unit, "i": i, "t": float(tt[i]), "type": typ, "dir": direction,
            "before": mean, "after": float(v[min(n - 1, i + w)])}


def analyse(rec: Recording, selected=None, t_from=None, t_to=None) -> list:
    sigs = [s for k, s in enumerate(rec.signals) if selected is None or k in selected]
    evs = [e for e in (detect(rec.t, s, t_from, t_to) for s in sigs) if e]
    return sorted(evs, key=lambda e: e["t"])


def events_text(rec: Recording, events: list, selected=None) -> str:
    sigs = [s for k, s in enumerate(rec.signals) if selected is None or k in selected]
    lines = [f"Recording {rec.name}: {len(rec.signals)} signals, {len(rec.t)} samples, "
             f"{rec.t[0]:.2f} to {rec.t[-1]:.2f} {rec.t_label}."]
    lines.append("Signals (min / mean / max):")
    for s in sigs[:40]:
        lines.append(f"- {s.name} [{s.unit}]: {s.v.min():.3g} / {s.v.mean():.3g} / {s.v.max():.3g}")
    if events:
        lines.append("Events detected automatically, in time order (first = most likely near the root cause):")
        for e in events:
            lines.append(f"- t={e['t']:.2f}: {e['signal']} {e['type']} {e['dir']} "
                         f"(before ≈{e['before']:.3g}, after ≈{e['after']:.3g} {e['unit']})")
    else:
        lines.append("No abnormal event detected in the selected signals.")
    return "\n".join(lines)


def decimate(t: np.ndarray, v: np.ndarray, width: int):
    """Min/max decimation for fast plotting: returns (t, v) with at most ~2*width points."""
    n = len(v)
    if n <= 2 * width:
        return t, v
    k = -(-n // width)
    m = (n // k) * k
    vv = v[:m].reshape(-1, k)
    tt = t[:m].reshape(-1, k)
    lo, hi = vv.argmin(1), vv.argmax(1)
    r = np.arange(vv.shape[0])
    first = np.minimum(lo, hi)
    second = np.maximum(lo, hi)
    t2 = np.empty(vv.shape[0] * 2)
    v2 = np.empty(vv.shape[0] * 2)
    t2[0::2], t2[1::2] = tt[r, first], tt[r, second]
    v2[0::2], v2[1::2] = vv[r, first], vv[r, second]
    return t2, v2
