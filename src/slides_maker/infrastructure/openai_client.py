from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import httpx


class OpenAIClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required")

    def chat(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        return {"content": content, "raw": data}

    def images(self, prompt: str, size: str = "1024x1024") -> bytes:
        url = f"{self.base_url}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": os.environ.get("OPENAI_IMAGE_MODEL", "").strip() or "gpt-image-1",
            "prompt": prompt,
            "size": size,
        }
        with httpx.Client(timeout=120) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        image_url = data["data"][0].get("url")
        if not image_url:
            raise RuntimeError("Image URL missing in response")
        with httpx.Client(timeout=120) as client:
            image_resp = client.get(image_url)
            image_resp.raise_for_status()
            return image_resp.content
