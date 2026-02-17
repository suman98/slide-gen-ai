from __future__ import annotations

import io
import os
import sys
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
        return _fetch_image_bytes(url)


class UnsplashImageProvider:
    def generate(self, prompt: str) -> bytes:
        query = quote_plus(prompt)
        url = f"https://source.unsplash.com/featured/1024x1024/?{query}"
        return _fetch_image_bytes(url, follow_redirects=True)


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


def _fetch_image_bytes(url: str, follow_redirects: bool = False) -> bytes:
    headers = {
        "User-Agent": "slides-maker/1.0 (+https://github.com/suman98/slide-gen-ai)",
        "Accept": "image/*,*/*;q=0.8",
    }
    timeout = httpx.Timeout(15.0, connect=10.0)
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=follow_redirects, headers=headers) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.content
        except Exception as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Image download failed")


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
        require_real = os.environ.get("REQUIRE_REAL_IMAGES", "0") == "1"
        if require_real:
            raise RuntimeError(
                "Image generation failed. Disable REQUIRE_REAL_IMAGES or allow placeholders."
            )
        print(
            "Image generation failed; using placeholder. "
            "Set REQUIRE_REAL_IMAGES=1 to fail instead.",
            file=sys.stderr,
        )
        return self._placeholder_image(prompt)


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
