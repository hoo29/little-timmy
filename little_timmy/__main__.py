import argparse
import logging
import json
import os
import sys

from ansible.plugins.loader import init_plugin_loader

from .config_loader import setup_run
from .duplicated_var_finder import find_duplicated_vars
from .unused_var_finder import find_unused_vars

VERSION = "3.0.0"
LOGGER = logging.getLogger("little-timmy")

# must be run only once
init_plugin_loader()


def main():
    parser = argparse.ArgumentParser(description="Process a directory path")
    parser.add_argument("directory", nargs="?", default=".",
                        type=str, help="The directory to process")

    parser.add_argument(
        "-c", "--config-file", type=str, help="Config file to use. By default it will search all dirs to `/` for .little-timmy")
    parser.add_argument("-d", "--dave-mode", default=False, action=argparse.BooleanOptionalAction,
                        help="Make logging work on dave's macbook.")
    parser.add_argument("-du", "--duplicated-vars", default=True, action=argparse.BooleanOptionalAction,
                        help="Find duplicated variables.")
    parser.add_argument("-e", "--exit-success", default=False, action=argparse.BooleanOptionalAction,
                        help="Exit 0 when unused vars are found.")
    parser.add_argument("-g", "--github-action", default=False, action=argparse.BooleanOptionalAction,
                        help="Output results for github actions.")
    parser.add_argument("-j", "--json-output", default=False, action=argparse.BooleanOptionalAction,
                        help="Output results as json to stdout. Disables the stderr logger.")
    parser.add_argument("-l", "--log-level", default="INFO", type=str,
                        help="set the logging level (default: INFO).")
    parser.add_argument("-u", "--unused-vars", default=True, action=argparse.BooleanOptionalAction,
                        help="Find unused variables.")
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

    context = setup_run(directory, args.config_file)
    if args.unused_vars:
        find_unused_vars(context)
    if args.duplicated_vars:
        find_duplicated_vars(context)

    if args.json_output:
        output = json.dumps(
            [{"name": k, "type": "UNUSED", "locations": list(v)}
             for k, v in context.all_unused_vars.items()]
            +
            [{"name": k, "type": "DUPLICATED", "locations": list(v.locations), "original": v.original}
             for k, v in context.all_duplicated_vars.items()], indent=4)
        print(output, file=sys.stdout)
    else:
        LOGGER.info("\n**unused vars**\n")
        for var_name, var_locations in context.all_unused_vars.items():
            print(f"""{var_name} at {[os.path.relpath(
                x, directory) for x in var_locations]}\n""", file=sys.stdout)
        LOGGER.info("\n**duplicated vars**\n")
        for var_name, var_details in context.all_duplicated_vars.items():
            print(f"""{var_name}""", file=sys.stdout)
            print(f"""at {[os.path.relpath(
                x, directory) for x in var_details.locations]}""", file=sys.stdout)
            print(
                f"""original {os.path.relpath(var_details.original, directory)}\n""", file=sys.stdout)

    if args.github_action:
        level = "warning" if args.exit_success else "error"
        for var_name, var_locations in context.all_unused_vars.items():
            for loc in var_locations:
                msg = f"::{level} file={loc}::{var_name} is unused"
                print(msg, file=sys.stderr)
        for var_name, var_details in context.all_duplicated_vars.items():
            for loc in var_details.locations:
                msg = f"::{level} file={loc}::{var_name} is duplicated"
                print(msg, file=sys.stderr)

    exit_code = 1
    if args.exit_success:
        exit_code = 0
    if not context.all_unused_vars and not context.all_duplicated_vars:
        exit_code = 0
        LOGGER.debug("no unused vars")
    LOGGER.debug("finished")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
