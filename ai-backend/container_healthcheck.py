"""HTTP health probe used by the nested-lab Quadlet containers."""

from __future__ import annotations

import os
import sys
from urllib.request import urlopen


def main() -> int:
    url = os.environ.get("AI_SERVER_HEALTH_URL", "").strip()
    if not url:
        print("AI_SERVER_HEALTH_URL is required.", file=sys.stderr)
        return 2

    try:
        with urlopen(url, timeout=3) as response:
            if response.status != 200:
                print("Health endpoint returned a non-200 response.", file=sys.stderr)
                return 1
    except OSError as error:
        print(f"Health endpoint request failed ({type(error).__name__}).", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
