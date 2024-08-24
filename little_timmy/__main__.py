import argparse
import logging
import json
import os
import sys

from .config_loader import find_and_load_config
from .var_finder import find_unused_vars

LOGGER = logging.getLogger("little-timmy")


def main():
    parser = argparse.ArgumentParser(description="Process a directory path")
    parser.add_argument("directory", nargs="?", default=".",
                        type=str, help="The directory to process")

    parser.add_argument(
        "-c", "--config-file", type=str, help="Config file to use. By default it will search all dirs to `/` for .little-timmy")
    parser.add_argument("-d", "--dave-mode", default=False, action=argparse.BooleanOptionalAction,
                        help="Make logging work on dave's macbook")
    parser.add_argument("-e", "--exit-success", default=False, action=argparse.BooleanOptionalAction,
                        help="Exit 0 when unused vars are found.")
    parser.add_argument("-j", "--json-output", default=False, action=argparse.BooleanOptionalAction,
                        help="Output results as json to stdout. Disables the stderr logger.")
    parser.add_argument("-l", "--log-level", default="INFO", type=str,
                        help="set the logging level (default: INFO)")
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
    LOGGER.debug("starting")

    if args.directory == ".":
        directory = os.getcwd()
    else:
        directory = args.directory

    config = find_and_load_config(directory, args.config_file)
    all_declared_vars = find_unused_vars(directory, config)

    LOGGER.debug("\n **unused vars** \n")
    if args.json_output:
        output = json.dumps([{"name": k, "locations": list(v)}
                             for k, v in all_declared_vars.items()], indent=4)
        stdout_logger = logging.getLogger("jsonresults")
        stdout_log_handler = logging.StreamHandler(sys.stdout)
        stdout_log_handler.setFormatter(logging.Formatter("%(message)s"))
        stdout_logger.propagate = False
        stdout_logger.addHandler(stdout_log_handler)
        stdout_logger.critical(output)
    else:
        for var_name, var_locations in all_declared_vars.items():
            LOGGER.info(f"""{var_name} at {[os.path.relpath(
                x, directory) for x in var_locations]}\n""")

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
