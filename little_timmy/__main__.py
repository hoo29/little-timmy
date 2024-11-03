import argparse
import logging
import json
import os
import sys

from .config_loader import find_and_load_config
from .var_finder import find_unused_vars

VERSION = "2.1.1"
LOGGER = logging.getLogger("little-timmy")


def main():
    parser = argparse.ArgumentParser(description="Process a directory path")
    parser.add_argument("directory", nargs="?", default=".",
                        type=str, help="The directory to process")

    parser.add_argument(
        "-c", "--config-file", type=str, help="Config file to use. By default it will search all dirs to `/` for .little-timmy")
    parser.add_argument("-d", "--dave-mode", default=False, action=argparse.BooleanOptionalAction,
                        help="Make logging work on dave's macbook.")
    parser.add_argument("-e", "--exit-success", default=False, action=argparse.BooleanOptionalAction,
                        help="Exit 0 when unused vars are found.")
    parser.add_argument("-g", "--github-action", default=False, action=argparse.BooleanOptionalAction,
                        help="Output results for github actions.")
    parser.add_argument("-j", "--json-output", default=False, action=argparse.BooleanOptionalAction,
                        help="Output results as json to stdout. Disables the stderr logger.")
    parser.add_argument("-l", "--log-level", default="INFO", type=str,
                        help="set the logging level (default: INFO).")
    parser.add_argument("-v", "--version", default=False, action=argparse.BooleanOptionalAction,
                        help="Output the version.")
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")
    if args.dave_mode:
        stderr_log_handler = logging.StreamHandler(stream=sys.stderr)
        stderr_log_handler.setLevel(log_level)
        stderr_log_handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(stderr_log_handler)
    logging.basicConfig(level=log_level, format="%(message)s")
    if args.json_output:
        LOGGER.disabled = True

    if args.version:
        LOGGER.info(VERSION)
        sys.exit(0)

    LOGGER.debug("starting")

    if args.directory == ".":
        directory = os.getcwd()
    else:
        directory = args.directory

    if directory.endswith("/"):
        directory = directory[:-1]

    config = find_and_load_config(directory, args.config_file)
    all_declared_vars = find_unused_vars(directory, config)

    LOGGER.debug("\n **unused vars** \n")
    if args.json_output:
        output = json.dumps([{"name": k, "locations": list(v)}
                             for k, v in all_declared_vars.items()], indent=4)
        print(output, file=sys.stdout)
    else:
        for var_name, var_locations in all_declared_vars.items():
            print(f"""{var_name} at {[os.path.relpath(
                x, directory) for x in var_locations]}\n""", file=sys.stdout)

    if args.github_action:
        level = "warning" if args.exit_success else "error"
        for var_name, var_locations in all_declared_vars.items():
            for loc in var_locations:
                msg = f"::{level} file={loc}::{var_name} is unused"
                print(msg, file=sys.stderr)

    exit_code = 1
    if args.exit_success:
        exit_code = 0
    if not all_declared_vars:
        exit_code = 0
        LOGGER.debug("no unused vars")
    LOGGER.debug("finished")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
