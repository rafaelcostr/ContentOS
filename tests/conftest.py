"""Shared pytest environment defaults."""

from __future__ import annotations

import os

os.environ["DEBUG"] = "true"
os.environ.setdefault("JWT_SECRET", "test-secret-hardening-32-characters")
