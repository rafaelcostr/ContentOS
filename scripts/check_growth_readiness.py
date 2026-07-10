"""Print Growth OAuth/publishing readiness for local setup."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for package_src in (
    ROOT / "packages" / "growth" / "src",
):
    sys.path.insert(0, str(package_src))

from contentos_growth.application.growth_readiness import build_growth_readiness  # noqa: E402


def _line(status: str, label: str, detail: str) -> str:
    marker = {
        "ready": "[OK]",
        "missing": "[FALTA]",
        "manual": "[MANUAL]",
        "warning": "[AVISO]",
        "not_supported": "[INFO]",
    }.get(status, "[INFO]")
    return f"  {marker} {label} - {detail}"


def main() -> int:
    report = build_growth_readiness()
    data = report.to_dict()

    print("ContentOS Growth Readiness")
    print(f"Status: {data['status']}")
    print(f"Resumo: {data['summary']}")
    print("")

    print("Checks globais:")
    for check in data["global_checks"]:
        print(_line(check["status"], check["label"], check["detail"]))
        if check.get("manual_action"):
            print(f"    Ação: {check['manual_action']}")
    print("")

    print("Plataformas:")
    for platform in data["platforms"]:
        print(f"- {platform['label']} ({platform['status']})")
        for check in platform["checks"]:
            print(_line(check["status"], check["label"], check["detail"]))
            if check.get("manual_action"):
                print(f"    Ação: {check['manual_action']}")
    print("")

    print("Próximos passos:")
    for step in data["next_steps"]:
        print(f"- {step}")

    return 1 if report.status == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
