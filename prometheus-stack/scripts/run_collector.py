import argparse
import sys

from config import Settings
from collector import Collector


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run tesla_collector (once or loop)")
    parser.add_argument("--once", action="store_true", help="Run one collection cycle and exit")
    args = parser.parse_args(argv)

    settings = Settings()
    c = Collector(settings)

    try:
        if args.once:
            c.run_once()
        else:
            c.run_forever()
    except KeyboardInterrupt:
        print("Interrupted, exiting")
        sys.exit(0)


if __name__ == "__main__":
    main()
