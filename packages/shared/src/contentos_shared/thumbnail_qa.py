"""Thumbnail validation — size and vertical aspect checks."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


@dataclass
class ThumbnailQaReport:
    passed: bool
    width: int = 0
    height: int = 0
    size_bytes: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "thumbnail_qa_passed": self.passed,
            "thumbnail_width": self.width,
            "thumbnail_height": self.height,
            "thumbnail_size_bytes": self.size_bytes,
            "thumbnail_qa_errors": self.errors,
        }


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None
    offset = 2
    while offset < len(data) - 1:
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if offset + 7 > len(data):
                return None
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        if marker in {0xD8, 0xD9}:
            break
        if offset + 2 > len(data):
            break
        segment_len = struct.unpack(">H", data[offset : offset + 2])[0]
        offset += segment_len
    return None


def validate_thumbnail(
    image_bytes: bytes,
    *,
    min_bytes: int = 5_000,
    min_width: int = 720,
    min_height: int = 1080,
) -> ThumbnailQaReport:
    """Validate thumbnail bytes for publish readiness."""
    errors: list[str] = []
    size = len(image_bytes or b"")
    if size < min_bytes:
        errors.append(f"Thumbnail too small ({size} bytes, min {min_bytes})")

    dims = _jpeg_dimensions(image_bytes)
    width = height = 0
    if dims is None:
        errors.append("Could not parse JPEG dimensions")
    else:
        width, height = dims
        if width < min_width or height < min_height:
            errors.append(f"Thumbnail resolution too low ({width}x{height})")
        elif height <= width:
            errors.append(f"Thumbnail not vertical ({width}x{height})")

    return ThumbnailQaReport(
        passed=not errors,
        width=width,
        height=height,
        size_bytes=size,
        errors=errors,
    )
