import argparse
import sys

from .export import export_directory


def main():
    parser = argparse.ArgumentParser(description="Synthetic CSV pseudonymization v1")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("export")
    command.add_argument("--input", required=True)
    command.add_argument("--output", required=True)
    command.add_argument("--seed", required=True)
    args = parser.parse_args()
    try:
        export_directory(args.input, args.output, args.seed)
    except (ValueError, OSError) as error:
        print("export error: {}".format(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
