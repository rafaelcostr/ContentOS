"""Local thumbnail generation — frame extract + text overlay."""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
from typing import Any


class LocalThumbnailProvider:
    """Generate thumbnails without cloud ImageProvider (ffmpeg + Pillow)."""

    async def generate(
        self,
        *,
        title: str,
        topic: str,
        render_ref: dict[str, Any] | None,
        asset_manager,
        concept: dict[str, Any] | None = None,
    ) -> bytes:
        concept = concept or {}
        overlay = str(concept.get("overlay_text") or title or topic)[:40]
        if render_ref and asset_manager:
            frame = await self._extract_frame(asset_manager, render_ref)
            if frame:
                return self._overlay_text(frame, overlay)
        return self._placeholder(overlay, concept)

    async def _extract_frame(self, asset_manager, render_ref: dict[str, Any]) -> bytes | None:
        key = render_ref.get("key")
        bucket = render_ref.get("bucket")
        if not key:
            return None
        try:
            from uuid import UUID

            from contentos_shared.enums import AssetCategory
            from contentos_shared.schemas.asset import AssetRef

            ref = AssetRef(
                id=UUID(str(render_ref.get("id"))) if render_ref.get("id") else UUID(int=0),
                category=AssetCategory.RENDERS,
                key=key,
                bucket=bucket or "",
                content_type="video/mp4",
            )
            video_bytes = await asset_manager.get(ref)
        except Exception:
            return None
        ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vf:
            vf.write(video_bytes)
            video_path = vf.name
        out_path = video_path + ".jpg"
        try:
            subprocess.run(
                [ffmpeg, "-y", "-i", video_path, "-vframes", "1", "-q:v", "2", out_path],
                check=True,
                capture_output=True,
                timeout=60,
            )
            with open(out_path, "rb") as f:
                return f.read()
        except Exception:
            return None
        finally:
            for p in (video_path, out_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _overlay_text(self, image_bytes: bytes, text: str) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = img.resize((1080, 1920))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 72)
            except OSError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (1080 - tw) // 2
            y = 1920 - th - 120
            draw.rectangle([x - 20, y - 10, x + tw + 20, y + th + 10], fill=(0, 0, 0, 180))
            draw.text((x, y), text, fill="white", font=font)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return buf.getvalue()
        except ImportError:
            return image_bytes

    def _placeholder(self, text: str, concept: dict[str, Any]) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont

            hint = str(concept.get("visual_hint") or "bold contrast")
            color = (30, 30, 80) if "dark" in hint.lower() else (20, 60, 120)
            img = Image.new("RGB", (1080, 1920), color=color)
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 64)
            except OSError:
                font = ImageFont.load_default()
            draw.text((80, 800), text, fill="white", font=font)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return buf.getvalue()
        except ImportError:
            return self._minimal_jpeg()

    def _minimal_jpeg(self) -> bytes:
        # 1x1 gray JPEG fallback when Pillow unavailable
        return bytes.fromhex(
            "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
            "070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c"
            "231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b"
            "0c180d0d1832211c213232323232323232323232323232323232323232323232"
            "323232323232323232323232323232323232ffc0000b08000100010001100100"
            "0211020311ffc4001f0000010501010101010100000000000000000102030405"
            "060708090a0bffc400b5100002010303020403050504040000017d0102030004"
            "110521314106127151813291061441522191a1071542b1c1323352f816170829"
            "90a161718191a25262728292a3435363738393a434445464748494a53545556"
            "5758595a636465666768696a737475767778797a838485868788898a92939495"
            "969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9"
            "cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9fa"
            "ffc4001f0100030101010101010101010000000000000102030405060708090a"
            "0bffc400b5110002010204040304070504040001027700010203110405213106"
            "1241510761711322328108144191a1c109233352f0156272d10a162434e092f"
            "011627374435363738393a535455565758595a636465666768696a7374757677"
            "78797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2"
            "b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5"
            "e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c03010002110311003f00fbbf"
            "d2ffcfd9"
        )
