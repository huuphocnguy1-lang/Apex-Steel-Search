# -*- mode: python ; coding: utf-8 -*-
# Build:  pyinstaller --noconfirm packaging/ApexSteelSearch.spec
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [(os.path.join(ROOT, "assets"), "assets")]
binaries = []
hiddenimports = ["apex_search.gui.main_window", "fitz", "pymupdf", "pillow_heif", "extract_msg", "iba_py",
                 "watchdog.observers", "watchdog.observers.read_directory_changes"]

for pkg in ("rapidocr_onnxruntime", "extract_msg", "RTFDE"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

try:  # iba .dat reader: bundle it under whatever import name the package really uses
    import sys as _sys
    from PyInstaller.utils.hooks import collect_submodules, copy_metadata
    _sys.path.insert(0, ROOT)
    from apex_search.iba import _dist_top_levels
    _tops = _dist_top_levels("iba-py")
    print("iba-py top-level modules:", _tops)
    for _t in _tops:
        hiddenimports.append(_t)
        hiddenimports += collect_submodules(_t)
    datas += copy_metadata("iba-py")
except Exception as e:
    print("WARNING: iba-py not bundled:", e)

for pkg in ("ezdxf", "pptx", "docx"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "PyQt5", "PyQt6", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ApexSteelSearch",
    console=False,
    icon=os.path.join(ROOT, "assets", "icon.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ApexSteelSearch", upx=False)
