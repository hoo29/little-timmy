import argparse
import logging
import os
import sys

from .config_loader import find_and_load_config
from .var_finder import find_unused_vars

LOGGER = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Process a directory path")
    parser.add_argument("directory", nargs="?", default=".",
                        type=str, help="The directory to process")
    parser.add_argument("-l", "--log-level", default="INFO", type=str,
                        help="set the logging level (default: INFO)")
    parser.add_argument(
        "-c", "--config-file", type=str, help="Config file to use. By default it will search all dirs to `/` for .little-timmy")
    parser.add_argument("-d", "--dave-mode", default=False, action=argparse.BooleanOptionalAction,
                        help="Make logging work on dave's macbook")
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
    LOGGER.debug("starting")
    if args.directory == ".":
        directory = os.getcwd()
    else:
        directory = args.directory

    config = find_and_load_config(directory, args.config_file)

    all_declared_vars = find_unused_vars(directory, config)

    LOGGER.debug("\n **unused vars** \n")
    if not all_declared_vars:
        LOGGER.info("no unused vars")
    # filter out vars only declared in galaxy_roles and collections
    for var_name, var_locations in all_declared_vars.items():
        LOGGER.info(f"""{var_name} at {[os.path.relpath(
            x, directory) for x in var_locations]}\n""")

    LOGGER.debug("finished")


if __name__ == "__main__":
    main()
