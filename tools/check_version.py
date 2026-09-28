"""Fail if the app version disagrees anywhere it is written down.

config.APP_VERSION is the source of truth. The browser extension manifest,
the Inno Setup script and the docs can't import it, so this script checks
them instead. Run by CI:  python tools/check_version.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    config_src = (ROOT / "config.py").read_text(encoding="utf-8")
    version = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', config_src, re.M).group(1)

    found = {
        "Library of Yore Browser Extension/manifest.json": json.loads(
            (ROOT / "Library of Yore Browser Extension" / "manifest.json").read_text(encoding="utf-8")
        )["version"],
        "installer.iss": re.search(
            r'#define\s+MyAppVersion\s+"([^"]+)"', (ROOT / "installer.iss").read_text(encoding="utf-8")
        ).group(1),
        "README.md badge": re.search(
            r"badge/Version-([0-9.]+)-", (ROOT / "README.md").read_text(encoding="utf-8")
        ).group(1),
        "USER_MANUAL.md header": re.search(
            r"^\*\*Version ([0-9.]+)\*\*", (ROOT / "USER_MANUAL.md").read_text(encoding="utf-8"), re.M
        ).group(1),
        "CHANGELOG.md latest entry": re.search(
            r"^## \[([0-9.]+)\]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M
        ).group(1),
    }

    bad = {where: v for where, v in found.items() if v != version}
    if bad:
        print(f"config.APP_VERSION is {version}, but:")
        for where, v in bad.items():
            print(f"  {where}: {v}")
        return 1
    print(f"Version {version} is consistent across {len(found) + 1} places.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
