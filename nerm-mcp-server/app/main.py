import logging

from nerm.server import build_server


def main() -> None:
    server = build_server()
    try:
        server.run()
    except KeyboardInterrupt:
        logging.getLogger("nerm.main").info("Shutdown requested (Ctrl-C). Exiting gracefully.")
        raise SystemExit(0) from None


if __name__ == "__main__":
    main()
