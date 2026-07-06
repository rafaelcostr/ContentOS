"""Persist plugin install/enable state (PostgreSQL or JSON file)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contentos_plugins_core.infrastructure.discovery import plugins_root


class PluginStateRepository:
    def _state_file(self) -> Path:
        return plugins_root() / "state" / "plugins.json"

    def load_all(self) -> dict[str, dict[str, Any]]:
        db_states = self._load_from_db()
        if db_states:
            return db_states
        path = self._state_file()
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def set_installed(
        self,
        name: str,
        *,
        enabled: bool,
        version: str,
        source: str,
    ) -> None:
        states = self.load_all()
        states[name] = {
            "installed": True,
            "enabled": enabled,
            "version": version,
            "source": source,
            "installed_at": datetime.now(UTC).isoformat(),
        }
        self._save_all(states)
        self._save_to_db(name, enabled=enabled, version=version, source=source, installed=True)

    def set_enabled(self, name: str, enabled: bool) -> None:
        states = self.load_all()
        if name not in states:
            states[name] = {"installed": True, "version": "1.0.0", "source": "marketplace"}
        states[name]["enabled"] = enabled
        self._save_all(states)
        self._save_to_db(
            name,
            enabled=enabled,
            version=states[name].get("version", "1.0.0"),
            source=states[name].get("source", "marketplace"),
            installed=True,
        )

    def remove(self, name: str) -> None:
        states = self.load_all()
        states.pop(name, None)
        self._save_all(states)
        self._delete_from_db(name)

    def _save_all(self, states: dict[str, dict[str, Any]]) -> None:
        path = self._state_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(states, indent=2), encoding="utf-8")

    def _load_from_db(self) -> dict[str, dict[str, Any]]:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return {}
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        try:
            from contentos_database.models import InstalledPlugin
            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import Session

            engine = create_engine(sync_url, pool_pre_ping=True)
            with Session(engine) as session:
                rows = session.execute(select(InstalledPlugin)).scalars().all()
                return {
                    r.name: {
                        "installed": True,
                        "enabled": r.enabled,
                        "version": r.version,
                        "source": r.source,
                        "installed_at": r.installed_at.isoformat() if r.installed_at else None,
                    }
                    for r in rows
                }
        except Exception:
            return {}

    def _save_to_db(self, name: str, *, enabled: bool, version: str, source: str, installed: bool) -> None:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        try:
            from contentos_database.models import InstalledPlugin
            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import Session

            engine = create_engine(sync_url, pool_pre_ping=True)
            with Session(engine) as session:
                row = session.execute(select(InstalledPlugin).where(InstalledPlugin.name == name)).scalar_one_or_none()
                if row:
                    row.enabled = enabled
                    row.version = version
                    row.source = source
                else:
                    session.add(
                        InstalledPlugin(
                            id=uuid.uuid4(),
                            name=name,
                            version=version,
                            enabled=enabled,
                            source=source,
                            installed_at=datetime.now(UTC),
                        )
                    )
                session.commit()
        except Exception:
            pass

    def _delete_from_db(self, name: str) -> None:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        try:
            from contentos_database.models import InstalledPlugin
            from sqlalchemy import create_engine, delete
            from sqlalchemy.orm import Session

            engine = create_engine(sync_url, pool_pre_ping=True)
            with Session(engine) as session:
                session.execute(delete(InstalledPlugin).where(InstalledPlugin.name == name))
                session.commit()
        except Exception:
            pass
