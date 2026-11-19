<p align="center"><img src="assets/icon.png" width="96" alt="Apex Steel Analyser logo"></p>

<h1 align="center">Apex Steel Analyser</h1>
<p align="center">Search and analyse your site documents (drawings, PDF, Word, Excel, emails and photos) on your Windows laptop. Everything works offline.</p>

---

## Features

| | |
|---|---|
| 🔎 **Keyword search** | Searches the words inside PDF, Word, Excel, PowerPoint, TXT/CSV, Outlook emails, DXF/DWG title blocks, and text read by OCR. Filter by type, project or latest revision, then export the results to Excel. |
| 🧠 **Smart search** | Searches by meaning, in any language: “column foot fixing” also finds *anchor bolts*, *tiges d'ancrage* and *地脚螺栓*. |
| 💬 **AI assistant** | Ask questions about your documents. Every answer lists its sources, and a click opens the file. |
| 📷 **OCR** | Reads text in photos, scans and screenshots (Chinese, English, French), for example a nameplate, a column mark or a scanned NCR. |
| 📐 **Revisions** | Groups the revisions of each drawing automatically, flags the latest ✓, and compares two revisions line by line. |
| 🏷 **Library & tags** | Finds the drawing number, revision, project, steel grade and language automatically. |
| 🖼 **Similar photos** | Finds site photos that look like a chosen photo. |
| 🧬 **Duplicates** | Finds identical copies (Downloads, WeChat, USB…) and moves them to a `_to_delete` folder. |
| ⚡ **Fast** | Handles 10,000+ documents with searches under 0.2 s. Only new or changed files are indexed, and the index updates automatically. |
| 🛠 **Steel Specialist** | Troubleshooting for ESP, casting, hot strip mill, pay-off reel, laminar cooling and hydraulics: what I see → likely causes → checks → actions → safety. Accepts photos and uses your lessons learned. Includes a casting temperature calculator (liquidus, tundish, ladle). |
| 📈 **iba Analyzer** | Open CSV/TXT exported from ibaAnalyzer: stacked signals, zoom, comparison with a normal reference, automatic event detection (🥇 first signal to move) and AI explanation. |
| 🔧 **Hydraulics** | Open a hydraulic schematic PDF, drag a box around a zone and the AI explains components, function, oil flow and faults. Includes calculators (cylinder, pump, accumulator) and ISO 4406 targets. |
| 📒 **Lessons learned** | Log of solved problems (symptom, root cause, fix), used automatically by the Steel Specialist. |
| 📑 **Drawing types** | Recognises mechanical drawings, hydraulic schematics, P&IDs and electrical schematics, with filters in Search and Library. |
| 🔒 **Offline / ☁ Online** | Offline keeps all data on your laptop. Online lets the assistant use a cloud AI (Qwen, DeepSeek…). |

## Get the app (no programming needed)

1. Push this project to GitHub (see below). **GitHub Actions builds the app automatically** in about 10 minutes.
2. On GitHub, open **Actions → Build Windows app → the latest run → Artifacts** and download `ApexSteelSearch-…-windows`.
3. Inside you'll find:
   - `ApexSteelSearch-Setup-x.y.z.exe`: the installer, which creates a desktop shortcut (recommended)
   - `ApexSteelSearch-portable-…-win64.zip`: unzip it anywhere and run `ApexSteelSearch.exe`

> Windows may show “Windows protected your PC” because the app is not signed. Click **More info → Run anyway**.

### Make a Release (download page)
```bash
git tag v0.1.0
git push origin v0.1.0
```
GitHub then publishes the installer and the zip under **Releases**.

## First start

1. Click **＋ Add folder** and choose your project folders (for example `D:\Projects`, your Apex Steel photos, `Downloads`).
2. Indexing runs in the background, and you can search while it works. OCR of photos and scans is the slowest part (about 1–3 s per image), so leave the first indexing running overnight if you have many photos.
3. Search!

## Optional extras

### Smart search + AI assistant, offline (recommended)
1. Install **Ollama**: https://ollama.com/download
2. In a terminal:
   ```
   ollama pull qwen2.5:7b
   ollama pull bge-m3
   ollama pull qwen2.5vl:7b     (photos)
   ```
3. In the app, go to **Settings → Test AI connection**, then **Folders & index → 🧠 Build smart index**.

Recommended: 16 GB RAM. With 8 GB RAM, use `qwen2.5:3b`.

### Online AI (optional)
**Settings → Online AI**: enter the API address, key and model. Any OpenAI-compatible service works:
- Qwen (Alibaba DashScope): `https://dashscope.aliyuncs.com/compatible-mode/v1`, models `qwen-max` / `text-embedding-v3`
- DeepSeek: `https://api.deepseek.com/v1`, model `deepseek-chat`

Then switch the top-right toggle to **☁ Online**.

### DWG drawings
Install the free **ODA File Converter** (opendesign.com → Guest files), then set its path in **Settings**. DXF files work without it.

## Where are my data?
- Index and settings: `%LOCALAPPDATA%\ApexSteelSearch\` (`index.db`, `settings.json`, `app.log`)
- **Your files are never modified.** The only exception is when you ask to move duplicates to `_to_delete`.

## For developers

```bat
run_dev.bat        :: run from source (creates .venv, installs requirements)
build_exe.bat      :: build dist\ApexSteelSearch\ApexSteelSearch.exe locally
```
or manually:
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
python run.py
```

Project layout:
```
apex_search/
  config.py      settings
  db.py          SQLite index (FTS5 trigram full-text, works for Chinese) + AI vectors
  extract.py     text extraction for each file type
  ocr.py         RapidOCR (offline)
  meta.py        drawing number / revision / project / steel grade / language / photo hash
  indexer.py     folder scanning, incremental updates, smart index
  search.py      keyword, smart (hybrid) search, AI assistant with sources, revision diff
  ai.py          Ollama + OpenAI-compatible clients
  gui/           PySide6 interface (main_window.py, pages.py, common.py)
packaging/       PyInstaller spec + Inno Setup installer
.github/workflows/build-windows.yml   automatic build
docs/simulation.html                  clickable design preview
```

## Push to GitHub (first time)
```bash
cd apex-steel-search
git init
git add .
git commit -m "Apex Steel Search v0.1.0"
git branch -M main
git remote add origin https://github.com/<your-account>/Apex-Steel-Search.git
git push -u origin main
```
