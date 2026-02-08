from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
from PIL import Image, ImageDraw, ImageFont

from slides_maker.infrastructure.openai_client import OpenAIClient


class ImageProvider(Protocol):
    def generate(self, prompt: str) -> bytes:
        ...


class OpenAIImageProvider:
    def __init__(self, client: OpenAIClient | None = None) -> None:
        self.client = client or OpenAIClient()

    def generate(self, prompt: str) -> bytes:
        return self.client.images(prompt=prompt)


class StockImageProvider:
    def generate(self, prompt: str) -> bytes:
        seed = abs(hash(prompt)) % 10_000
        url = f"https://picsum.photos/seed/{seed}/1024/1024"
        with httpx.Client(timeout=60) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content


@dataclass
class ImageService:
    output_dir: Path
    primary: ImageProvider
    fallback: ImageProvider | None = None

    def generate_image(self, prompt: str, filename: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / filename
        try:
            content = self.primary.generate(prompt)
        except Exception:
            if self.fallback is not None:
                try:
                    content = self.fallback.generate(prompt)
                except Exception:
                    content = self._placeholder_image(prompt)
            else:
                content = self._placeholder_image(prompt)

        target.write_bytes(content)
        return target

    def _placeholder_image(self, prompt: str) -> bytes:
        image = Image.new("RGB", (1024, 1024), color=(240, 240, 240))
        draw = ImageDraw.Draw(image)
        text = (prompt[:60] + "...") if len(prompt) > 60 else prompt
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((40, 40), text, fill=(60, 60, 60), font=font)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


def build_image_service(output_dir: Path) -> ImageService:
    use_openai = os.environ.get("USE_OPENAI_IMAGES", "0") == "1"
    primary: ImageProvider
    if use_openai:
        primary = OpenAIImageProvider()
        fallback: ImageProvider | None = StockImageProvider()
    else:
        primary = StockImageProvider()
        fallback = None
    return ImageService(output_dir=output_dir, primary=primary, fallback=fallback)
