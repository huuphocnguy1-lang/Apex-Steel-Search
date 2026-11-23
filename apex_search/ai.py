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


class _StreamUnsupported(Exception):
    pass


def _stream(url: str, payload: dict, headers: dict | None, timeout: int):
    """Yields text lines of a streaming HTTP answer (Ollama NDJSON or OpenAI-style SSE)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    opener = _NO_PROXY if _is_local(url) else urllib.request.build_opener()
    try:
        with opener.open(req, timeout=timeout) as r:
            ctype = r.headers.get("Content-Type", "")
            if "json" in ctype and "ndjson" not in ctype and "stream" in payload and not _is_local(url):
                body = r.read().decode("utf-8", "ignore")   # server ignored stream=True
                d = json.loads(body)
                yield "data: " + json.dumps({"choices": [{"delta": {"content": d["choices"][0]["message"]["content"]}}]})
                return
            for raw in r:
                line = raw.decode("utf-8", "ignore").strip()
                if line:
                    yield line
    except urllib.error.HTTPError as e:
        body = e.read()[:400].decode("utf-8", "ignore")
        raise AIError(f"HTTP {e.code} from {url}: {body}") from None
    except urllib.error.URLError as e:
        raise AIError(f"Cannot reach {url} ({e.reason}). Is the AI engine running?") from None
    except TimeoutError:
        raise AIError(f"Timeout calling {url}") from None


class _ThinkFilter:
    """Hides <think>…</think> blocks (models that think inside the text) and forwards the rest."""

    def __init__(self, on_token=None):
        self.on_token, self.buf, self.out, self.inside = on_token, "", [], False

    def feed(self, piece: str):
        self.buf += piece
        while True:
            if self.inside:
                i = self.buf.find("</think>")
                if i < 0:
                    self.buf = self.buf[-8:]
                    return
                self.buf = self.buf[i + 8:]
                self.inside = False
            else:
                i = self.buf.find("<think>")
                if i < 0:
                    keep = 6 if "<" in self.buf[-6:] else 0     # a tag may be split between pieces
                    emit, self.buf = (self.buf[:-keep], self.buf[-keep:]) if keep else (self.buf, "")
                    self._emit(emit)
                    return
                self._emit(self.buf[:i])
                self.buf = self.buf[i + 7:]
                self.inside = True

    def _emit(self, t):
        if t:
            if not self.out:
                t = t.lstrip()
                if not t:
                    return
            self.out.append(t)
            if self.on_token:
                try:
                    self.on_token(t)
                except Exception:
                    pass

    def text(self) -> str:
        if self.buf and not self.inside:
            self._emit(self.buf)
            self.buf = ""
        return "".join(self.out).strip()


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

    # ------------------------------------------------------------ chat (streaming, fast)
    def _is_thinking_model(self, model: str) -> bool:
        m = (model or "").lower()
        return any(k in m for k in ("qwen3", "deepseek-r1", "qwq", "magistral", "gpt-oss"))

    def chat(self, messages: list[dict], images: list[str] | None = None, on_token=None, deep: bool | None = None,
             model: str | None = None, max_tokens: int | None = None, keep_alive: str | None = None) -> str:
        """Returns the full answer. on_token(text) is called with each new piece as it is written.
        images: base64 JPEG strings attached to the last user message (uses the vision model).
        deep: allow the model to 'think' first (slower). Default from Settings (off = fast)."""
        deep = self.cfg.get("deep_thinking", False) if deep is None else deep
        msgs = [dict(m) for m in messages]
        flt = _ThinkFilter(on_token)
        if self.online:
            model = self.cfg.get("cloud_vision_model") if images else (model or self.cfg["cloud_chat_model"])
            if images:
                msgs[-1]["content"] = [{"type": "text", "text": msgs[-1]["content"]}] + [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}"}} for b in images]
            payload = {"model": model, "messages": msgs, "temperature": 0.2, "stream": True}
            if max_tokens:
                payload["max_tokens"] = int(max_tokens)
            if not deep and "qwen3" in (model or "").lower():
                payload["enable_thinking"] = False
            try:
                for line in _stream(self._cloud("/chat/completions"), payload, self._cloud_headers(), 240):
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        d = json.loads(data)
                        piece = (d.get("choices") or [{}])[0].get("delta", {}).get("content") or ""
                    except (ValueError, AttributeError, IndexError):
                        piece = ""
                    if piece:
                        flt.feed(piece)
            except _StreamUnsupported:
                payload["stream"] = False
                r = _post(self._cloud("/chat/completions"), payload, self._cloud_headers(), timeout=240)
                flt.feed(r["choices"][0]["message"]["content"] or "")
            return flt.text()
        model = self.cfg.get("local_vision_model") if images else (model or self.cfg["local_chat_model"])
        if images:
            msgs[-1]["images"] = images
        thinking = self._is_thinking_model(model)
        if thinking and not deep and msgs and msgs[-1].get("role") == "user" and "qwen3" in model.lower():
            msgs[-1]["content"] = str(msgs[-1]["content"]) + "\n/no_think"
        payload = {"model": model, "messages": msgs, "stream": True,
                   "keep_alive": keep_alive or self.cfg.get("keep_alive", "60m"),
                   "options": {"temperature": 0.2, "num_ctx": int(self.cfg.get("num_ctx", 6144))}}
        if max_tokens:
            payload["options"]["num_predict"] = int(max_tokens)
        if thinking:
            payload["think"] = bool(deep)
        try:
            for line in _stream(self._ollama("/api/chat"), payload, None, 900):
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("error"):
                    raise AIError(str(d["error"]))
                piece = (d.get("message") or {}).get("content") or ""
                if piece:
                    flt.feed(piece)
                if d.get("done"):
                    break
        except AIError as e:
            if images and ("not found" in str(e) or "404" in str(e)):
                raise AIError(f"The picture model '{model}' is not installed. Open cmd and run:  ollama pull {model}") from None
            if "think" in str(e).lower() and "think" in payload:   # old Ollama without the think option
                payload.pop("think")
                return self._chat_plain(payload, flt)
            raise
        return flt.text()

    def _chat_plain(self, payload, flt):
        payload = dict(payload, stream=False)
        r = _post(self._ollama("/api/chat"), payload, timeout=900)
        flt.feed(r["message"]["content"] or "")
        return flt.text()

    # ------------------------------------------------------------ local models: list, GPU use, install
    def local_models(self) -> list[str]:
        try:
            return [m.get("name", "") for m in _get(self._ollama("/api/tags"), timeout=5).get("models", [])]
        except Exception:
            return []

    def has_local_model(self, name: str) -> bool:
        n = (name or "").strip().lower()
        if not n:
            return False
        names = [m.lower() for m in self.local_models()]
        return n in names or (":" not in n and f"{n}:latest" in names)

    def gpu_status(self) -> str:
        """Where the loaded models run: 'GPU 100 %', 'CPU only', … (from Ollama /api/ps)."""
        try:
            ms = _get(self._ollama("/api/ps"), timeout=5).get("models", [])
        except Exception:
            return "unknown (Ollama not reachable)"
        if not ms:
            return "no model loaded yet"
        out = []
        for m in ms:
            size, vram = m.get("size") or 0, m.get("size_vram") or 0
            pct = round(100 * vram / size) if size else 0
            where = "CPU only" if pct == 0 else ("GPU 100 %" if pct >= 99 else f"GPU {pct} % / CPU {100 - pct} %")
            out.append(f"{m.get('name')}: {where}")
        return " · ".join(out)

    def pull_model(self, name: str, on_progress=None) -> str:
        """Downloads a model into Ollama (like 'ollama pull name'). on_progress(text) gets status lines."""
        last = ""
        for line in _stream(self._ollama("/api/pull"), {"name": name, "stream": True}, None, 3600):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("error"):
                raise AIError(str(d["error"]))
            st = d.get("status", "")
            if d.get("total"):
                st += f" {100 * (d.get('completed') or 0) // d['total']} %"
            if on_progress and st != last:
                on_progress(st)
            last = st
        return f"✔ {name} installed"

    def warm_up(self):
        """Loads the local chat model in memory (so the first question is fast)."""
        if self.online:
            return
        try:
            _post(self._ollama("/api/generate"), {"model": self.cfg["local_chat_model"], "prompt": "",
                                                  "keep_alive": self.cfg.get("keep_alive", "60m")}, timeout=300)
        except Exception:
            pass

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
