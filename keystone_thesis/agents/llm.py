"""Minimal client for any OpenAI-compatible chat endpoint (OpenAI, OpenRouter,
Groq, Together, a local Ollama server, ...). Standard library only.

Configure with environment variables (see ``.env.example``):
  KEYSTONE_LLM_API_KEY   your key (falls back to OPENAI_API_KEY)
  KEYSTONE_LLM_BASE_URL  default https://api.openai.com/v1
  KEYSTONE_LLM_MODEL     default gpt-4o-mini

The LLM never produces a score. Scores come from the deterministic engine;
the LLM only maps companies to themes when keywords fail, and writes prose.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class LLMError(RuntimeError):
    pass


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None, timeout: int = 90):
        _load_dotenv()
        self.api_key = api_key or os.getenv("KEYSTONE_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("KEYSTONE_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("KEYSTONE_LLM_MODEL") or "gpt-4o-mini"
        self.timeout = timeout
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise LLMError("No LLM key found. Set KEYSTONE_LLM_API_KEY in .env, or run without --llm.")

    def chat(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 1500) -> str:
        body = json.dumps({
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMError(f"LLM request failed: HTTP {exc.code} {exc.read()[:300]!r}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"LLM request failed: {exc.reason}") from exc
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected LLM response: {str(payload)[:300]}") from exc

    def chat_json(self, system: str, user: str, required: List[str], retries: int = 2) -> Dict[str, Any]:
        """Ask for JSON, strip code fences, check required keys, retry on failure."""
        last = ""
        for _ in range(retries + 1):
            text = self.chat(system + "\nRespond with ONLY valid JSON, no prose.", user + last)
            cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
            try:
                data = json.loads(cleaned)
                if all(k in data for k in required):
                    return data
                last = f"\n\nYour last answer was missing keys {required}. Try again."
            except json.JSONDecodeError:
                last = "\n\nYour last answer was not valid JSON. Try again."
        raise LLMError("LLM did not return valid JSON after retries")
