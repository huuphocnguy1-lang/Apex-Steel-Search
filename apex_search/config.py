"""Settings stored as JSON in %LOCALAPPDATA%\\ApexSteelSearch (Windows) or ~/.apex_steel_search."""
import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    # Folders to index: list of {"path": str, "enabled": bool}
    "folders": [],
    # "offline" = everything local. "online" = the AI assistant uses the cloud model.
    "mode": "offline",
    # Local AI through Ollama (https://ollama.com) — optional
    "ollama_url": "http://localhost:11434",
    "local_chat_model": "qwen2.5:7b",
    "local_embed_model": "bge-m3",
    # Cloud AI, any OpenAI-compatible API (Qwen/DashScope, DeepSeek, ...)
    "cloud_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "cloud_api_key": "",
    "cloud_chat_model": "qwen-max",
    "cloud_embed_model": "text-embedding-v3",
    # Models that understand pictures (used when a photo is attached in the chat)
    "local_vision_model": "qwen2.5vl:7b",
    "cloud_vision_model": "qwen-vl-max",
    # Which engine builds the smart-search index: "local" or "cloud"
    "embed_provider": "local",
    # Speed of the local AI
    "deep_thinking": False,        # Qwen3 & co: think before answering (much slower)
    "keep_alive": "60m",           # keep the model loaded in memory between questions
    "num_ctx": 6144,
    "answer_cache_days": 7,
    # Night analysis: pre-read and summarise important folders when the laptop is not used
    "night_folders": [],
    "night_auto": False,
    "night_start": "22:00",
    "night_only_idle": True,
    "sum_skip_drawings": True,      # night analysis: skip drawing sheets (they stay searchable)
    "sum_latest_rev_only": True,    # only the latest revision of a document number, one copy of duplicates
    "sum_short": True,              # short summaries (3000 characters read, ~60 words written) = 2x faster
    "summary_model_local": "qwen3:4b",   # small fast model for summaries ('' = use the chat model)
    "summary_model_cloud": "",           # e.g. qwen-plus / qwen-turbo ('' = use the cloud chat model)
    # Knowledge library (built-in expert notes + Learn from web) — indexed like a watched folder
    "knowledge_enabled": True,
    "kn_engine": "auto",            # auto = Bing → Bing China → DuckDuckGo
    "kn_per_query": 2,              # pages kept per search query
    "kn_wikipedia": True,
    "kn_ai_notes": False,           # also ask the online AI model to write a note per topic
    "kn_topics": ["ESP", "PS", "HYD-SERVO", "HYD-TROUBLE"],
    # Build smart index automatically after each scan (needs the AI engine running)
    "auto_smart": True,
    # OCR (text in photos and scanned PDFs)
    "ocr_enabled": True,
    "ocr_max_pdf_pages": 30,
    # DWG support: path to ODA File Converter (free download)
    "oda_path": r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    # Project code found in the file path, e.g. P-2401
    "project_regex": r"\bP-?\d{3,5}\b",
    # Skip files bigger than this (MB)
    "max_file_mb": 500,
    "excluded_dirs": ["_to_delete", "$RECYCLE.BIN", "System Volume Information",
                      "node_modules", "__pycache__", ".git"],
}


def data_dir() -> Path:
    base = os.environ.get("APEX_SEARCH_HOME")
    if not base:
        if sys.platform == "win32":
            base = os.path.join(os.environ.get("LOCALAPPDATA", str(Path.home())), "ApexSteelSearch")
        else:
            base = os.path.join(str(Path.home()), ".apex_steel_search")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


class Config(dict):
    def __init__(self, path: Path | None = None):
        super().__init__(DEFAULTS)
        self.path = Path(path) if path else data_dir() / "settings.json"
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.update(json.load(f))
        except FileNotFoundError:
            pass
        except Exception:
            # corrupt settings: keep defaults, keep a backup
            try:
                os.replace(self.path, str(self.path) + ".bak")
            except OSError:
                pass

    def save(self):
        tmp = str(self.path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dict(self), f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def enabled_folders(self) -> list[str]:
        out = [f["path"] for f in self.get("folders", []) if f.get("enabled", True) and os.path.isdir(f["path"])]
        if self.get("knowledge_enabled", True):
            try:
                from .knowledge import root
                out.append(root())
            except Exception:
                pass
        return out
