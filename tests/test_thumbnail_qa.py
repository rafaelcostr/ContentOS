"""Thumbnail QA validation tests."""

from contentos_shared.thumbnail_qa import validate_thumbnail


def _minimal_jpeg(width: int, height: int, pad: int = 6000) -> bytes:
    """Build a minimal valid JPEG with SOF0 marker."""
    header = bytes(
        [
            0xFF,
            0xD8,
            0xFF,
            0xE0,
            0x00,
            0x10,
            0x4A,
            0x46,
            0x49,
            0x46,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x01,
            0x00,
            0x01,
            0x00,
            0x00,
            0xFF,
            0xC0,
            0x00,
            0x0B,
            0x08,
            (height >> 8) & 0xFF,
            height & 0xFF,
            (width >> 8) & 0xFF,
            width & 0xFF,
            0x01,
            0x11,
            0x00,
            0xFF,
            0xD9,
        ]
    )
    return header + (b"\x00" * pad)


def test_validate_thumbnail_passes_vertical():
    data = _minimal_jpeg(1080, 1920)
    report = validate_thumbnail(data)
    assert report.passed is True
    assert report.width == 1080
    assert report.height == 1920


def test_validate_thumbnail_fails_landscape():
    data = _minimal_jpeg(1920, 1080)
    report = validate_thumbnail(data)
    assert report.passed is False
    assert any("vertical" in err for err in report.errors)


def test_validate_thumbnail_fails_too_small():
    data = _minimal_jpeg(1080, 1920, pad=100)
    report = validate_thumbnail(data)
    assert report.passed is False
    assert any("small" in err for err in report.errors)
