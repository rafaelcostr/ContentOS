"""Local image generation — vertical thumbnail via Pillow (no cloud API)."""

from __future__ import annotations

import io
import os
import re


class LocalImageAdapter:
    """ImageProvider for short-form thumbnails (1080x1920 default)."""

    name = "local"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "pillow-thumbnail"

    async def generate_image(self, prompt: str, size: str = "1080x1920") -> bytes:
        width, height = self._parse_size(size)
        overlay = self._overlay_from_prompt(prompt)
        return self._render(overlay, width, height)

    @staticmethod
    def _parse_size(size: str) -> tuple[int, int]:
        match = re.match(r"(\d+)\s*[xX]\s*(\d+)", size.strip())
        if not match:
            return 1080, 1920
        return int(match.group(1)), int(match.group(2))

    @staticmethod
    def _overlay_from_prompt(prompt: str) -> str:
        text = (prompt or "ContentOS").strip()
        # Prefer first line / short title segment
        for sep in ("\n", " | ", " — ", " - "):
            if sep in text:
                text = text.split(sep, 1)[0]
        return text[:48]

    def _render(self, text: str, width: int, height: int) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise RuntimeError("Pillow is required for LocalImageAdapter") from exc

        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Gradient-like bands
        for y in range(height):
            ratio = y / max(height, 1)
            r = int(15 + ratio * 40)
            g = int(23 + ratio * 20)
            b = int(42 + ratio * 80)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        accent = (56, 189, 248)
        draw.rectangle([0, height - 24, width, height], fill=accent)

        font_size = max(36, width // 14)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = max(24, (width - tw) // 2)
        y = max(24, (height - th) // 2)
        # Shadow
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0))
        draw.text((x, y), text, font=font, fill=(248, 250, 252))

        buf = io.BytesIO()
        quality = int(os.getenv("THUMBNAIL_JPEG_QUALITY", "90"))
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
