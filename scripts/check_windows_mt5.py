from __future__ import annotations

import importlib.metadata
import importlib.util
import platform
import sys


REQUIRED_PACKAGES = ("MetaTrader5", "PyYAML", "cryptography", "ctrader-open-api")


def package_status(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT INSTALLED"


def main() -> int:
    failures = 0
    print("Python:", platform.python_version())
    print("Operating system:", platform.system())

    if platform.system() != "Windows":
        print("CHECK: FAIL - MetaTrader 5 integration requires Windows.")
        failures += 1
    else:
        print("CHECK: PASS - Windows detected.")

    for package in REQUIRED_PACKAGES:
        version = package_status(package)
        print(f"{package}: {version}")
        if version == "NOT INSTALLED":
            failures += 1

    if importlib.util.find_spec("MetaTrader5") is None:
        print("MetaTrader5 import: unavailable")
    else:
        print("MetaTrader5 import: available")

    if sys.version_info < (3, 10):
        print("CHECK: FAIL - Python 3.10 or newer is required.")
        failures += 1

    if failures:
        print("DEPENDENCY_CHECK: FAIL")
        print("Install dependencies with: py -m pip install -r requirements.txt")
        return 1

    print("DEPENDENCY_CHECK: PASS")
    print("No broker connection or trade was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
