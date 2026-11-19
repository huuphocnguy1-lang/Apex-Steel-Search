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
    start: datetime.datetime | None = None

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


DAT_HELP = ("If this .dat cannot be read directly (some iba file versions are not supported by the open-source "
            "reader), export it from ibaAnalyzer to ASCII/CSV and open the exported file here.")


def _as_array(x):
    try:
        a = np.asarray(x, dtype=float).ravel()
        return a if a.size else None
    except (TypeError, ValueError):
        return None


def _as_datetime(x):
    if isinstance(x, datetime.datetime):
        return x
    if isinstance(x, (int, float)) and x > 1e8:
        return datetime.datetime.fromtimestamp(x)
    if isinstance(x, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(x[:26], fmt)
            except ValueError:
                continue
    return None


def _from_decoded(path, begin, interval, data) -> Recording:
    """Converts what the dat decoder returns into a Recording (tolerant to several data layouts)."""
    chans = []   # (name, unit, t or None, values, dt)
    items = data.items() if isinstance(data, dict) else (
        [(c[0], c[1]) for c in data] if isinstance(data, (list, tuple)) else [])
    for name, val in items:
        unit, t, v, dt = "", None, None, None
        if isinstance(val, dict):
            unit = str(val.get("unit") or val.get("Unit") or "")
            for k in ("values", "data", "y", "v", "Values"):
                if k in val:
                    v = _as_array(val[k])
                    break
            for k in ("t", "time", "timestamps", "x"):
                if k in val:
                    t = _as_array(val[k])
                    break
            dt = val.get("interval") or val.get("dt")
        else:
            v = _as_array(val)
        if v is None:
            continue
        if dt is None:
            dt = interval.get(name) if isinstance(interval, dict) else interval
        try:
            dt = float(dt) if dt else None
        except (TypeError, ValueError):
            dt = None
        chans.append((str(name), unit, t, v, dt))
    if not chans:
        raise ValueError("No analog signals found in this .dat file. " + DAT_HELP)
    base = max(chans, key=lambda c: len(c[3]))
    tb = base[2] if base[2] is not None and len(base[2]) == len(base[3]) else np.arange(len(base[3])) * (base[4] or 1.0)
    signals = []
    for name, unit, t, v, dt in chans:
        tc = t if t is not None and len(t) == len(v) else np.arange(len(v)) * (dt or (tb[-1] / max(1, len(v) - 1)))
        vv = v if (len(v) == len(tb) and np.allclose(tc, tb)) else np.interp(tb, tc, v)
        m = re.match(r"^(.*?)\s*[\[(]([^\])]{1,10})[\])]\s*$", name)
        if m and not unit:
            name, unit = m.group(1).strip(), m.group(2)
        signals.append(Signal(name, unit, vv.astype(float)))
    return Recording(path=path, t=np.asarray(tb, dtype=float), signals=signals, t_label="s",
                     start=_as_datetime(begin))


def _dist_top_levels(dist_name: str = "iba-py") -> list[str]:
    """Top-level module names installed by a distribution (its import name may differ from 'iba_py')."""
    from importlib.metadata import distribution
    d = distribution(dist_name)
    names = (d.read_text("top_level.txt") or "").split()
    for f in d.files or []:
        f = str(f).replace("\\", "/")
        if f.endswith(".py") and "/" not in f:
            names.append(f[:-3])
        elif f.endswith("/__init__.py") and f.count("/") == 1:
            names.append(f.split("/")[0])
    return [n for n in dict.fromkeys(names) if n and not n.endswith(".dist-info")]


_DEC = None


def _find_dec():
    """Finds the decoder function dec() of iba-py, whatever the package's import name is."""
    global _DEC
    if _DEC:
        return _DEC
    import importlib
    errors, names = [], []
    try:
        names += _dist_top_levels()
    except Exception as e:
        errors.append(f"package metadata: {type(e).__name__}: {e}")
    names += ["iba_py", "iba_py.iba", "iba_py.core", "iba"]
    for n in dict.fromkeys(names):
        if n.split(".")[0] in ("apex_search",):
            continue
        try:
            m = importlib.import_module(n)
        except Exception as e:
            errors.append(f"{n}: {type(e).__name__}: {e}")
            continue
        f = getattr(m, "dec", None)
        if callable(f):
            _DEC = (f, n)
            return _DEC
        for sub in ("iba", "core", "dat", "main", "__main__"):
            try:
                sm = importlib.import_module(f"{n}.{sub}")
                f = getattr(sm, "dec", None)
                if callable(f):
                    _DEC = (f, f"{n}.{sub}")
                    return _DEC
            except Exception:
                pass
        errors.append(f"{n}: imported but has no dec()")
    raise ImportError(" | ".join(errors) or "iba-py not found")


def dat_reader_status() -> tuple[bool, str]:
    """(ok, text) — shown in Settings so a missing or broken .dat reader is easy to diagnose."""
    try:
        from importlib.metadata import version
        v = version("iba-py")
    except Exception:
        v = None
    try:
        _, mod = _find_dec()
    except Exception as e:
        return False, (f"iba-py {v} installed but not usable — " if v else "iba-py not installed — ") + str(e)[:300]
    return True, f"iba-py {v or '?'} ready (module '{mod}')"


def load_dat(path: str) -> Recording:
    try:
        dec, _ = _find_dec()
    except Exception as e:
        raise ValueError(f"The .dat reader (iba-py) could not be loaded ({str(e)[:300]}). " + DAT_HELP) from None
    try:
        begin, interval, data = dec(path)
    except Exception as e:
        raise ValueError(f"This .dat file could not be decoded ({type(e).__name__}: {e}). " + DAT_HELP) from None
    return _from_decoded(path, begin, interval, data)


def load(path: str) -> Recording:
    if os.path.splitext(path)[1].lower() == ".dat":
        return load_dat(path)
    return load_csv(path)


def load_many(paths: list[str]) -> dict:
    """Loads several files; returns {'recs': [...], 'errors': [(file, message)]}. Sorted by start time / name."""
    recs, errors = [], []
    for p in paths:
        try:
            recs.append(load(p))
        except Exception as e:
            errors.append((os.path.basename(p), str(e)))
    recs.sort(key=lambda r: (r.start or datetime.datetime.min, r.name))
    return {"recs": recs, "errors": errors}


def join(recs: list[Recording]) -> Recording:
    """Joins consecutive recordings (same signals) into one long recording in time order."""
    if len(recs) == 1:
        return recs[0]
    recs = sorted(recs, key=lambda r: (r.start or datetime.datetime.min, r.name))
    names = [s.name for s in recs[0].signals if all(any(x.name == s.name for x in r.signals) for r in recs[1:])]
    t_parts, v_parts = [], {n: [] for n in names}
    offset = 0.0
    t0 = recs[0].start
    for r in recs:
        if t0 and r.start:
            off = (r.start - t0).total_seconds()
        else:
            off = offset
        tt = r.t - r.t[0] + off
        t_parts.append(tt)
        for n in names:
            v_parts[n].append(next(s for s in r.signals if s.name == n).v)
        step = float(np.median(np.diff(r.t))) if len(r.t) > 1 else 1.0
        offset = tt[-1] + step
    t = np.concatenate(t_parts)
    order = np.argsort(t, kind="stable")
    sigs = []
    for n in names:
        unit = next(s.unit for s in recs[0].signals if s.name == n)
        sigs.append(Signal(n, unit, np.concatenate(v_parts[n])[order]))
    label = f"s from {t0:%Y-%m-%d %H:%M:%S}" if t0 else "s"
    return Recording(path=f"{len(recs)} files joined ({recs[0].name} … {recs[-1].name})", t=t[order], signals=sigs,
                     t_label=label, start=t0)


def scan_files(recs: list[Recording], names: list[str] | None = None) -> list[dict]:
    """Event analysis of every file: which files have events and which signal moved first."""
    rows = []
    for k, r in enumerate(recs):
        sel = {i for i, s in enumerate(r.signals) if names is None or s.name in names}
        ev = analyse(r, sel)
        rows.append({"index": k, "file": r.name, "start": r.start, "events": len(ev),
                     "first": ev[0]["signal"] if ev else "", "t": ev[0]["t"] if ev else None,
                     "type": f"{ev[0]['type']} {ev[0]['dir']}" if ev else ""})
    return rows


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
