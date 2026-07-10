from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUTOPILOT_FILE_NAMES = {
    "autopilot.py",
    "autonomous_calendar.py",
    "autonomous_execution.py",
    "closed_loop.py",
}

BANNED_IMPORT_PREFIXES = (
    "celery",
    "kombu",
    "contentos_agents",
    "contentos_workflow.tasks",
)

BANNED_CALL_ATTRIBUTES = {
    "delay",
    "apply_async",
}


def _autopilot_python_files() -> list[Path]:
    files: list[Path] = []
    growth_app = ROOT / "packages" / "growth" / "src" / "contentos_growth" / "application"
    if growth_app.exists():
        files.extend(path for path in growth_app.glob("*.py") if path.name in AUTOPILOT_FILE_NAMES)

    autopilot_pkg = ROOT / "packages" / "autopilot"
    if autopilot_pkg.exists():
        files.extend(path for path in autopilot_pkg.rglob("*.py") if "__pycache__" not in path.parts)

    return sorted(files)


def _module_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return None
    if isinstance(node, ast.ImportFrom):
        return node.module
    return None


def _import_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    module = _module_name(node)
    return [module] if module else []


def test_autopilot_architecture_files_exist():
    files = _autopilot_python_files()
    names = {path.name for path in files}
    assert AUTOPILOT_FILE_NAMES.issubset(names)


def test_autopilot_does_not_import_execution_layers():
    violations: list[str] = []
    for path in _autopilot_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Import | ast.ImportFrom):
                continue
            for name in _import_names(node):
                if name.startswith(BANNED_IMPORT_PREFIXES):
                    violations.append(f"{path.relative_to(ROOT)} imports {name}")

    assert violations == []


def test_autopilot_does_not_call_celery_shortcuts():
    violations: list[str] = []
    for path in _autopilot_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in BANNED_CALL_ATTRIBUTES:
                    violations.append(f"{path.relative_to(ROOT)} calls .{node.func.attr}()")

    assert violations == []
