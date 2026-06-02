"""Native Python LLM client using OpenAI-compatible API."""

import json
import urllib.request
import urllib.error
from typing import Optional

from doc_pipeline_native.config import LLMConfig


class LLMClient:
    """HTTP-based LLM client - no external dependencies required."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }

    def generate(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None) -> str:
        """Send a prompt to the LLM and return the response text."""
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        url = f"{self.base_url}/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=self.headers, method="POST")

        print(f"[LLM Call] model={self.config.model}, sytem={system_prompt[:60]!r}, user={len(user_prompt)}")
        
        try:
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"LLM API error ({e.code}): {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"LLM connection error: {e.reason}")
