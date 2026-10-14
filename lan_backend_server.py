"""Run the backend on the configured private LAN address using HTTPS."""

import sys

from lan_test_config import PROJECT_ROOT, load_lan_test_config


def main() -> None:
    config = load_lan_test_config()
    sys.path.insert(0, str(PROJECT_ROOT / "ai-backend"))
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.host,
        port=8000,
        ssl_certfile=str(config.certificate),
        ssl_keyfile=str(config.private_key),
    )


if __name__ == "__main__":
    main()
