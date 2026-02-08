from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import quote_plus

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


class UnsplashImageProvider:
    def generate(self, prompt: str) -> bytes:
        query = quote_plus(prompt)
        url = f"https://source.unsplash.com/featured/1024x1024/?{query}"
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content


class ChainedImageProvider:
    def __init__(self, providers: list[ImageProvider]) -> None:
        self.providers = providers

    def generate(self, prompt: str) -> bytes:
        last_exc: Exception | None = None
        for provider in self.providers:
            try:
                return provider.generate(prompt)
            except Exception as exc:
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("No image providers configured")


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
                    content = self._handle_image_failure(prompt)
            else:
                content = self._handle_image_failure(prompt)

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

    def _handle_image_failure(self, prompt: str) -> bytes:
        allow_placeholder = os.environ.get("ALLOW_PLACEHOLDER_IMAGES", "0") == "1"
        if allow_placeholder:
            return self._placeholder_image(prompt)
        raise RuntimeError("Image generation failed. Set ALLOW_PLACEHOLDER_IMAGES=1 to allow placeholders.")


def build_image_service(output_dir: Path) -> ImageService:
    use_openai = os.environ.get("USE_OPENAI_IMAGES", "0") == "1"
    primary: ImageProvider
    if use_openai:
        primary = ChainedImageProvider(
            [OpenAIImageProvider(), UnsplashImageProvider(), StockImageProvider()]
        )
        fallback: ImageProvider | None = None
    else:
        primary = ChainedImageProvider([UnsplashImageProvider(), StockImageProvider()])
        fallback = None
    return ImageService(output_dir=output_dir, primary=primary, fallback=fallback)
