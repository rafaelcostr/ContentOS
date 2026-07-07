"""V5.1.2 — project voice library."""

from __future__ import annotations

from uuid import uuid4

import pytest
from contentos_shared.voice.profile import BUILTIN_PROFILES, resolve_builtin_profile
from contentos_shared.voice.project_library import load_project_builtin_default_sync


def test_load_project_builtin_default_sync_empty_without_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert load_project_builtin_default_sync(uuid4()) is None


def test_builtin_profiles_cover_expected_names():
    assert set(BUILTIN_PROFILES) == {"default", "hype", "calm", "documentary"}


@pytest.mark.asyncio
async def test_voice_library_service_snapshot():
    from contentos_database.models import ProjectMemory, VoiceProfile
    from contentos_gateway.services.voice_library_service import VoiceLibraryService

    project_id = uuid4()
    profile_id = uuid4()

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            class S:
                def __init__(self, data):
                    self._data = data

                def all(self):
                    return self._data

            return S(self._rows)

        def scalar_one_or_none(self):
            return self._rows[0] if self._rows else None

    class FakeSession:
        def __init__(self):
            self.memory = ProjectMemory(project_id=project_id, default_voice_builtin="hype")
            self.profiles = [
                VoiceProfile(
                    id=profile_id,
                    project_id=project_id,
                    name="Projeto X",
                    slug="projeto-x",
                    provider="piper",
                    voice_id=None,
                    speed=1.05,
                    pitch_semitones=0.5,
                    pause_ms=250,
                    is_default=False,
                )
            ]

        async def execute(self, stmt):
            return FakeResult(self.profiles)

        async def get(self, model, key):
            if model is ProjectMemory and key == project_id:
                return self.memory
            return None

        async def flush(self):
            return None

    service = VoiceLibraryService(FakeSession())
    library = await service.get_library(project_id)
    assert library.project_id == str(project_id)
    assert library.default_builtin == "hype"
    assert len(library.builtins) == 4
    assert len(library.custom) == 1
    hype = next(item for item in library.builtins if item.slug == "hype")
    assert hype.is_default is True


@pytest.mark.asyncio
async def test_set_default_builtin_clears_custom_flags():
    from contentos_database.models import ProjectMemory, VoiceProfile
    from contentos_gateway.services.voice_library_service import VoiceLibraryService

    project_id = uuid4()
    profile_id = uuid4()

    class FakeSession:
        def __init__(self):
            self.memory = ProjectMemory(project_id=project_id)
            self.profile = VoiceProfile(
                id=profile_id,
                project_id=project_id,
                name="Custom",
                slug="custom",
                provider="piper",
                is_default=True,
            )

        async def execute(self, stmt):
            rows = [self.profile]

            class ScalarResult:
                def __iter__(self_inner):
                    return iter(rows)

                def all(self_inner):
                    return list(rows)

            class Result:
                def scalars(self_inner):
                    return ScalarResult()

                def scalar_one_or_none(self_inner):
                    return None

            return Result()

        async def get(self, model, key):
            if model is ProjectMemory:
                return self.memory
            return None

        async def flush(self):
            return None

    session = FakeSession()
    service = VoiceLibraryService(session)
    library = await service.set_default(project_id, builtin_name="calm")
    assert session.profile.is_default is False
    assert session.memory.default_voice_builtin == "calm"
    calm = next(item for item in library.builtins if item.slug == "calm")
    assert calm.is_default is True


def test_resolve_builtin_profile_for_library():
    profile = resolve_builtin_profile("documentary")
    assert profile.name == "documentary"
    assert profile.speed < 1.0
