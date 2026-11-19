"""iba recordings: load signals exported from ibaAnalyzer (CSV / TXT), detect events, find the first signal that moved."""
import datetime
import os
import re
from dataclasses import dataclass, field

import numpy as np


class Signal:
    """A signal; its values can be loaded lazily (big iba files: only the signals you tick are read)."""

    def __init__(self, name: str, unit: str, v=None, loader=None):
        self.name, self.unit, self._v, self.loader = name, unit, v, loader

    @property
    def v(self) -> np.ndarray:
        if self._v is None:
            self._v = np.asarray(self.loader(), dtype=float) if self.loader else np.zeros(0)
        return self._v

    @v.setter
    def v(self, value):
        self._v = value

    @property
    def loaded(self) -> bool:
        return self._v is not None


@dataclass
class Recording:
    path: str
    t: np.ndarray
    signals: list = field(default_factory=list)
    t_label: str = "s"
    start: datetime.datetime | None = None
    info: dict = field(default_factory=dict)

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


def com_reader_status() -> tuple[bool, str]:
    try:
        from win32com import client
        with _Com():
            client.dynamic.Dispatch("IbaFilesLite.IbaFile")
        return True, "ibaFilesLite (iba official reader) ready — PDA3 files supported"
    except ImportError:
        return False, "pywin32 not available"
    except Exception as e:
        return False, f"ibaFilesLite.dll not registered ({str(e)[:100]})"


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


# ------------------------------------------------------------------ iba .dat through iba's own ibaFilesLite (COM)
DAT_COM_HELP = ("Your .dat files use iba's compressed format (PDA3). They are read through the installed ibaAnalyzer "
                "(64-bit, v7.4 or newer). If that failed, check that ibaAnalyzer opens the file normally. Alternative: iba's reader "
                "library ibaFilesLite.dll: if ibaAnalyzer or ibaDatCoordinator is installed, search your PC for "
                "'ibaFilesLite.dll' (64-bit) and register it once as administrator:  regsvr32 \"<path>\\ibaFilesLite.dll\"  "
                "— otherwise ask iba / your iba administrator for 'ibaFiles-Lite'.")


def dat_header_info(path: str) -> dict:
    """Readable fields in the iba file header, e.g. ME / HEAT / SEQ / SG / widths / temperatures (ESP coil info)."""
    try:
        head = open(path, "rb").read(8192).decode("latin-1")
    except OSError:
        return {}
    info = {}
    m = re.search(r"[A-Z][A-Za-z]{1,11}:[^\x00]{4,1500}?(?=\x00)", head)
    if m and "/" in m.group(0):
        for k, val in re.findall(r"/?([A-Za-z][A-Za-z0-9]{1,15}):([^/\x00]*)", m.group(0)):
            if val.strip():
                info[k] = val.strip()
    return info


class _Com:
    def __enter__(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        return self

    def __exit__(self, *a):
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
        return False


def _com_reader(path, preload=False):
    from win32com import client
    r = client.dynamic.Dispatch("IbaFilesLite.IbaFile")
    try:
        r.PreLoad = 1 if preload else 0
        r.RawMode = 0
    except Exception:
        pass
    r.Open(path)
    return r


def _com_channels(r):
    en = r.EnumChannels()
    while not en.IsAtEnd():
        yield en.Next()


def _q(obj, key, default=""):
    try:
        v = obj.QueryInfoByName(key)
        return default if v is None else v
    except Exception:
        return default


def _com_read(path: str, name: str, t_target: np.ndarray):
    from win32com import client
    import pythoncom
    with _Com():
        r = _com_reader(path)
        try:
            for ch in _com_channels(r):
                if str(_q(ch, "name")) != name:
                    continue
                var = client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 2)
                if ch.IsDefaultTimebased():
                    res = ch.QueryTimebasedData(0, 0, var)
                else:
                    res = ch.QueryLengthbasedData(0, 0, var)
                tb, xoff, data = (res[0], res[1], res[2]) if isinstance(res, tuple) and len(res) >= 3 else (None, 0, res)
                v = np.asarray(data, dtype=float).ravel()
                try:
                    tb = float(tb)
                except (TypeError, ValueError):
                    tb = 0.0
                if len(v) == len(t_target) or tb <= 0:
                    return v[:len(t_target)] if len(v) >= len(t_target) else np.interp(
                        t_target, np.linspace(t_target[0], t_target[-1], len(v)), v)
                tc = float(xoff or 0) + np.arange(len(v)) * tb
                return np.interp(t_target, tc, v)
        finally:
            try:
                r.Close()
            except Exception:
                pass
    raise ValueError(f"Signal {name} not found")


def load_dat_com(path: str) -> Recording:
    """Opens the file with iba's ibaFilesLite and lists the signals; values are read when a signal is ticked."""
    with _Com():
        r = _com_reader(path)
        try:
            clk = float(_q(r, "clk", 0) or 0)
            frames = int(float(_q(r, "frames", 0) or 0))
            st = str(_q(r, "starttime", ""))
            chans = []
            for ch in _com_channels(r):
                nm = str(_q(ch, "name")).strip()
                if not nm:
                    continue
                chans.append((nm, str(_q(ch, "unit")).strip(), str(_q(ch, "digchannel", "0")) in ("1", "True", "true")))
        finally:
            try:
                r.Close()
            except Exception:
                pass
    if not chans:
        raise ValueError("No signals found in this .dat file.")
    if clk <= 0 or frames <= 0:
        raise ValueError("The .dat file has no time base information.")
    t = np.arange(frames) * clk
    start = None
    for fmt in ("%d.%m.%Y %H:%M:%S.%f", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            start = datetime.datetime.strptime(st, fmt)
            break
        except ValueError:
            continue
    chans.sort(key=lambda c: c[2])           # analog first, digital after
    sigs = [Signal(nm + (" (digital)" if dig else ""), unit,
                   loader=(lambda n=nm: _com_read(path, n, t))) for nm, unit, dig in chans]
    return Recording(path=path, t=t, signals=sigs, t_label="s", start=start, info=dat_header_info(path))


# ------------------------------------------------------------------ iba .dat through the installed ibaAnalyzer (COM "IBA.Analyzer")
class _AnalyzerServer:
    """One dedicated thread owns the ibaAnalyzer COM object; every call is executed there (COM is thread-bound)."""

    def __init__(self):
        import queue
        import threading
        self.q = queue.Queue()
        self.app = None
        self.current = None
        self.t = threading.Thread(target=self._run, daemon=True, name="ibaAnalyzer-COM")
        self.t.start()

    def _run(self):
        with _Com():
            while True:
                fn, args, box, ev = self.q.get()
                try:
                    box["r"] = fn(self, *args)
                except Exception as e:
                    box["e"] = e
                ev.set()

    def call(self, fn, *args, timeout=600):
        import threading
        box, ev = {}, threading.Event()
        self.q.put((fn, args, box, ev))
        if not ev.wait(timeout):
            raise TimeoutError("ibaAnalyzer did not answer")
        if "e" in box:
            raise box["e"]
        return box["r"]

    # ---- executed inside the COM thread
    def ensure_app(self):
        if self.app is None:
            from win32com import client
            self.app = client.dynamic.Dispatch("IBA.Analyzer")
        return self.app

    def open(self, path):
        app = self.ensure_app()
        path = os.path.abspath(path)
        if self.current != path:
            if self.current:
                try:
                    app.CloseDataFile(0)
                except Exception:
                    pass
            app.OpenDataFile(0, path)
            self.current = path
        return app


_SERVER = None


def _server():
    global _SERVER
    if _SERVER is None:
        _SERVER = _AnalyzerServer()
    return _SERVER


def _an_walk(node, out, kind, depth=0):
    """Same traversal as known working tools: recursive into children, iterative over siblings."""
    guard = 0
    while node is not None and guard < 200_000:
        guard += 1
        try:
            text = str(node.Text or "")
        except Exception:
            text = ""
        try:
            cid = node.channelID
        except Exception:
            cid = None
        if cid not in (None, ""):
            name = text.split(": ", 1)[1] if ": " in text else (text or str(cid))
            out.append((str(cid), name.strip(), kind))
        try:
            node.Expand()
        except Exception:
            pass
        if depth < 30:
            try:
                child = node.GetFirstChildNode()
            except Exception:
                child = None
            if child is not None:
                _an_walk(child, out, kind, depth + 1)
        try:
            node = node.GetSiblingNode()
        except Exception:
            node = None


def _an_list(srv, path):
    import time
    app = srv.open(path)
    for attempt in range(4):
        out = []
        for kind, flt in (("analog", 1), ("digital", 2)):
            try:
                tree = app.GetSignalTree(flt)
                try:
                    root = tree.GetRootNode()
                except Exception:
                    root = tree
                _an_walk(root, out, kind)
            except Exception:
                continue
        if not out:   # some versions: only the combined tree
            try:
                tree = app.GetSignalTree(3)
                try:
                    root = tree.GetRootNode()
                except Exception:
                    root = tree
                _an_walk(root, out, "analog")
            except Exception:
                pass
        if out:
            seen, uniq = set(), []
            for c in out:
                if c[0] not in seen:
                    seen.add(c[0])
                    uniq.append(c)
            return uniq
        time.sleep(2.0 + attempt * 2)   # big files may still be loading in ibaAnalyzer
    return []


def _an_read(srv, path, cid):
    app = srv.open(path)
    r = app._oleobj_.InvokeTypes(82, 0, 1, (24, 0),
                                 ((8, 0), (3, 0), (16389, 2), (16389, 2), (16396, 2)),
                                 f"[{cid}]", 0, 0.0, 0.0, None)
    tb = float(r[0] or 0)
    xoff = float(r[1] or 0) if len(r) > 2 else 0.0
    data = np.asarray(r[2] if len(r) > 2 else r[1], dtype=float).ravel()
    return tb, xoff, data


def load_dat_analyzer(path: str) -> Recording:
    srv = _server()
    chans = srv.call(_an_list, path)
    if not chans:
        raise ValueError("ibaAnalyzer opened the file but listed no signals.")
    # time axis from the first analog signal
    t, tb0 = None, 0.0
    for cid, name, kind in chans:
        if kind != "analog":
            continue
        tb0, xoff, data = srv.call(_an_read, path, cid)
        if len(data) > 1:
            t = xoff + np.arange(len(data)) * (tb0 if tb0 > 0 else 1.0)
            break
    if t is None:
        raise ValueError("No analog data found in this file.")

    def reader(cid):
        tb, xoff, data = srv.call(_an_read, path, cid)
        if len(data) == len(t) or tb <= 0:
            return data[:len(t)] if len(data) >= len(t) else np.interp(t, np.linspace(t[0], t[-1], max(2, len(data))), data)
        return np.interp(t, xoff + np.arange(len(data)) * tb, data)

    sigs = [Signal(name + (" (digital)" if kind == "digital" else ""), "", loader=(lambda c=cid: reader(c)))
            for cid, name, kind in chans]
    start = None
    try:
        start = datetime.datetime.fromtimestamp(os.path.getmtime(path)) - datetime.timedelta(seconds=float(t[-1] - t[0]))
    except Exception:
        pass
    return Recording(path=path, t=t, signals=sigs, t_label="s", start=start, info=dat_header_info(path))


def _an_diagnose(srv, path):
    import time
    rep = []
    try:
        app = srv.ensure_app()
        rep.append(f"ibaAnalyzer version: {getattr(app, 'GetVersion', '?')}")
    except Exception as e:
        return f"Cannot start ibaAnalyzer: {e}"
    t0 = time.time()
    try:
        srv.current = None
        srv.open(path)
        rep.append(f"OpenDataFile OK ({time.time() - t0:.1f} s)")
    except Exception as e:
        rep.append(f"OpenDataFile FAILED: {e}")
        return "\n".join(rep)
    time.sleep(2)

    def desc(n, label):
        parts = []
        for attr in ("Text", "channelID", "ChannelID", "Name", "ID"):
            try:
                parts.append(f"{attr}={getattr(n, attr)!r}")
            except Exception as e:
                parts.append(f"{attr}=<{type(e).__name__}>")
        return f"{label}: " + ", ".join(parts)

    for flt in (3, 1, 2, 0):
        try:
            tree = app.GetSignalTree(flt)
            rep.append(f"GetSignalTree({flt}) -> {type(tree).__name__} {str(tree)[:60]}")
        except Exception as e:
            rep.append(f"GetSignalTree({flt}) FAILED: {e}")
            continue
        root = None
        for meth in ("GetRootNode", "RootNode", "Root"):
            try:
                r = getattr(tree, meth)
                root = r() if callable(r) else r
                rep.append(f"  tree.{meth} OK")
                break
            except Exception as e:
                rep.append(f"  tree.{meth} FAILED: {type(e).__name__}: {str(e)[:80]}")
        if root is None:
            root = tree
        rep.append("  " + desc(root, "root"))
        for step in ("Expand",):
            try:
                getattr(root, step)()
                rep.append("  root.Expand OK")
            except Exception as e:
                rep.append(f"  root.Expand FAILED: {str(e)[:80]}")
        try:
            child = root.GetFirstChildNode()
            rep.append(f"  root.GetFirstChildNode -> {'None' if child is None else 'node'}")
        except Exception as e:
            child = None
            rep.append(f"  root.GetFirstChildNode FAILED: {str(e)[:80]}")
        n = 0
        while child is not None and n < 6:
            rep.append("    " + desc(child, f"child {n}"))
            try:
                child.Expand()
            except Exception:
                pass
            try:
                g = child.GetFirstChildNode()
                m = 0
                while g is not None and m < 3:
                    rep.append("      " + desc(g, f"grandchild {m}"))
                    g = g.GetSiblingNode()
                    m += 1
            except Exception as e:
                rep.append(f"      grandchildren FAILED: {str(e)[:80]}")
            try:
                child = child.GetSiblingNode()
            except Exception as e:
                rep.append(f"    GetSiblingNode FAILED: {str(e)[:80]}")
                child = None
            n += 1
        if flt == 3:
            break
    for expr in ("[0:0]", "[0:1]", "[0.0]", "[1:0]"):
        try:
            r = app._oleobj_.InvokeTypes(82, 0, 1, (24, 0), ((8, 0), (3, 0), (16389, 2), (16389, 2), (16396, 2)),
                                         expr, 0, 0.0, 0.0, None)
            data = r[2] if len(r) > 2 else r[1]
            rep.append(f"read {expr}: timebase={r[0]!r} xoffset={r[1]!r} samples={len(data) if data is not None else None}")
        except Exception as e:
            rep.append(f"read {expr} FAILED: {str(e)[:100]}")
    return "\n".join(rep)


def diagnose_dat(path: str) -> str:
    try:
        return _server().call(_an_diagnose, path, timeout=300)
    except Exception as e:
        return f"Diagnostic failed: {type(e).__name__}: {e}"


def analyzer_status() -> tuple[bool, str]:
    try:
        srv = _server()
        v = srv.call(lambda s: str(s.ensure_app().GetVersion), timeout=60)
        return True, f"ibaAnalyzer {v} — PDA3 .dat files supported"
    except ImportError:
        return False, "pywin32 not available"
    except Exception as e:
        return False, f"ibaAnalyzer COM not available ({str(e)[:120]})"


def load_dat_any(path: str) -> Recording:
    errors = []
    try:
        return load_dat_analyzer(path)
    except Exception as e:
        errors.append(f"ibaAnalyzer: {type(e).__name__}: {str(e)[:200]}")
    try:
        return load_dat_com(path)
    except Exception as e:
        errors.append(f"iba reader: {type(e).__name__}: {str(e)[:200]}")
    try:
        rec = load_dat(path)
        rec.info = dat_header_info(path)
        return rec
    except Exception as e:
        errors.append(str(e)[:200])
    head = open(path, "rb").read(4)
    hint = DAT_COM_HELP if head == b"PDA3" else DAT_HELP
    raise ValueError(hint + "\n\nDetails: " + " | ".join(errors))


def load(path: str) -> Recording:
    if os.path.splitext(path)[1].lower() == ".dat":
        return load_dat_any(path)
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


def join(recs: list[Recording], only: list[str] | None = None) -> Recording:
    """Joins consecutive recordings (same signals) into one long recording in time order (values loaded lazily)."""
    if len(recs) == 1:
        return recs[0]
    recs = sorted(recs, key=lambda r: (r.start or datetime.datetime.min, r.name))
    names = [s.name for s in recs[0].signals if (only is None or s.name in only)
             and all(any(x.name == s.name for x in r.signals) for r in recs[1:])]
    t_parts, offset, t0 = [], 0.0, recs[0].start
    for r in recs:
        off = (r.start - t0).total_seconds() if (t0 and r.start) else offset
        tt = r.t - r.t[0] + off
        t_parts.append(tt)
        step = float(np.median(np.diff(r.t))) if len(r.t) > 1 else 1.0
        offset = tt[-1] + step
    t = np.concatenate(t_parts)
    order = np.argsort(t, kind="stable")

    def loader(n):
        return np.concatenate([next(s for s in r.signals if s.name == n).v for r in recs])[order]

    sigs = [Signal(n, next(s.unit for s in recs[0].signals if s.name == n), loader=(lambda n=n: loader(n)))
            for n in names]
    label = f"s from {t0:%Y-%m-%d %H:%M:%S}" if t0 else "s"
    return Recording(path=f"{len(recs)} files joined ({recs[0].name} … {recs[-1].name})", t=t[order], signals=sigs,
                     t_label=label, start=t0, info=recs[0].info)


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
    if rec.info:
        lines.append("File information: " + ", ".join(f"{k}={v}" for k, v in list(rec.info.items())[:25]))
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
