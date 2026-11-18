"""AI engines. Offline: Ollama on this laptop. Online: any OpenAI-compatible API (Qwen, DeepSeek...).
Uses only the Python standard library for HTTP."""
import json
import urllib.error
import urllib.request


class AIError(Exception):
    pass


def _post(url: str, payload: dict, headers: dict | None = None, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
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

    def chat(self, messages: list[dict]) -> str:
        if self.online:
            r = _post(self._cloud("/chat/completions"),
                      {"model": self.cfg["cloud_chat_model"], "messages": messages, "temperature": 0.2},
                      self._cloud_headers(), timeout=180)
            return r["choices"][0]["message"]["content"]
        r = _post(self._ollama("/api/chat"),
                  {"model": self.cfg["local_chat_model"], "messages": messages, "stream": False,
                   "options": {"temperature": 0.2}}, timeout=600)
        return r["message"]["content"]

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
