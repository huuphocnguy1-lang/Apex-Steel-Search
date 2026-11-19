"""AI engines. Offline: Ollama on this laptop. Online: any OpenAI-compatible API (Qwen, DeepSeek...).
Uses only the Python standard library for HTTP."""
import json
import urllib.error
import urllib.request


class AIError(Exception):
    pass


# Local AI (Ollama) must never go through a system proxy/VPN
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _is_local(url: str) -> bool:
    return any(h in url for h in ("://localhost", "://127.0.0.1", "://[::1]"))


def _get(url: str, timeout: int = 4) -> dict:
    opener = _NO_PROXY if _is_local(url) else urllib.request.build_opener()
    try:
        with opener.open(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise AIError(f"Cannot reach {url}: {getattr(e, 'reason', e)}") from None


def _post(url: str, payload: dict, headers: dict | None = None, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    opener = _NO_PROXY if _is_local(url) else urllib.request.build_opener()
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read()[:400].decode("utf-8", "ignore")
        raise AIError(f"HTTP {e.code} from {url}: {body}") from None
    except urllib.error.URLError as e:
        raise AIError(f"Cannot reach {url} ({e.reason}). Is the AI engine running?") from None
    except TimeoutError:
        raise AIError(f"Timeout calling {url}") from None


class AIClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    # ------------------------------------------------------------ helpers
    @property
    def online(self) -> bool:
        return self.cfg.get("mode") == "online"

    def _cloud_headers(self):
        key = self.cfg.get("cloud_api_key", "")
        if not key:
            raise AIError("No cloud API key set (Settings → Cloud AI)")
        return {"Authorization": f"Bearer {key}"}

    def _cloud(self, path):
        return self.cfg.get("cloud_base_url", "").rstrip("/") + path

    def _ollama(self, path):
        return self.cfg.get("ollama_url", "http://localhost:11434").rstrip("/") + path

    def chat_model_label(self) -> str:
        if self.online:
            return f"{self.cfg.get('cloud_chat_model')} (cloud)"
        return f"{self.cfg.get('local_chat_model')} (local, offline)"

    def embed_key(self) -> str:
        """Identifies which model produced the stored vectors."""
        if self.cfg.get("embed_provider") == "cloud":
            return "cloud:" + self.cfg.get("cloud_embed_model", "")
        return "local:" + self.cfg.get("local_embed_model", "")

    def embed_batch_size(self) -> int:
        return 10 if self.cfg.get("embed_provider") == "cloud" else 32

    # ------------------------------------------------------------ API
    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.cfg.get("embed_provider") == "cloud":
            if not self.online:
                raise AIError("Smart index uses the cloud model but the app is in Offline mode")
            r = _post(self._cloud("/embeddings"), {"model": self.cfg["cloud_embed_model"], "input": texts},
                      self._cloud_headers())
            return [d["embedding"] for d in sorted(r["data"], key=lambda d: d["index"])]
        r = _post(self._ollama("/api/embed"), {"model": self.cfg["local_embed_model"], "input": texts}, timeout=300)
        if "embeddings" not in r:
            raise AIError(f"Unexpected Ollama answer: {str(r)[:200]}")
        return r["embeddings"]

    def chat(self, messages: list[dict], images: list[str] | None = None) -> str:
        """images: base64 JPEG strings attached to the last user message (uses the vision model)."""
        msgs = [dict(m) for m in messages]
        if self.online:
            model = self.cfg.get("cloud_vision_model") if images else self.cfg["cloud_chat_model"]
            if images:
                msgs[-1]["content"] = [{"type": "text", "text": msgs[-1]["content"]}] + [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}} for b in images]
            r = _post(self._cloud("/chat/completions"),
                      {"model": model, "messages": msgs, "temperature": 0.2},
                      self._cloud_headers(), timeout=240)
            return r["choices"][0]["message"]["content"]
        model = self.cfg.get("local_vision_model") if images else self.cfg["local_chat_model"]
        if images:
            msgs[-1]["images"] = images
        try:
            r = _post(self._ollama("/api/chat"),
                      {"model": model, "messages": msgs, "stream": False, "options": {"temperature": 0.2}}, timeout=900)
        except AIError as e:
            if images and ("not found" in str(e) or "404" in str(e)):
                raise AIError(f"The picture model '{model}' is not installed. Open cmd and run:  ollama pull {model}") from None
            raise
        return r["message"]["content"]

    def check_embed_ready(self) -> str:
        """Quick check before building the smart index. Raises AIError with a clear, actionable message."""
        if self.cfg.get("embed_provider") == "cloud":
            if not self.online:
                raise AIError("The smart index is set to use the cloud model, but the app is in Offline mode.\n"
                              "Switch to Online, or choose 'Local (Ollama)' in Settings → Smart index.")
            self._cloud_headers()
            self.embed(["test"])
            return f"cloud model {self.cfg.get('cloud_embed_model')}"
        base = self.cfg.get("ollama_url", "http://localhost:11434").rstrip("/")
        try:
            tags = _get(base + "/api/tags")
        except AIError:
            raise AIError("Ollama is not running on this laptop.\n\n"
                          "1. Install Ollama from https://ollama.com/download\n"
                          "2. Open a terminal (cmd) and run:   ollama pull bge-m3\n"
                          "3. Click 'Build smart index' again.") from None
        names = [m.get("name", "") for m in tags.get("models", [])]
        want = self.cfg.get("local_embed_model", "bge-m3")
        if not any(n == want or n.split(":")[0] == want.split(":")[0] for n in names):
            raise AIError(f"Ollama is running, but the model '{want}' is not installed.\n\n"
                          f"Open a terminal (cmd) and run:   ollama pull {want}\n"
                          f"Installed models: {', '.join(names) or 'none'}")
        self.embed(["test"])
        return f"local model {want}"

    def test(self) -> str:
        lines = []
        try:
            v = self.embed(["anchor bolt M36"])
            lines.append(f"✔ Smart search model OK ({self.embed_key()}, {len(v[0])} dimensions)")
        except Exception as e:
            lines.append(f"✘ Smart search model: {e}")
        try:
            a = self.chat([{"role": "user", "content": "Reply with the single word: OK"}])
            lines.append(f"✔ Chat model OK ({self.chat_model_label()}): {a.strip()[:40]}")
        except Exception as e:
            lines.append(f"✘ Chat model: {e}")
        return "\n".join(lines)
