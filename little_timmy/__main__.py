import logging
import argparse

from .var_finder import find_unused_vars

LOGGER = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Process a directory path.")
    parser.add_argument("directory", nargs="?", default=".",
                        type=str, help="The directory to process")
    parser.add_argument("--log", default="INFO", type=str,
                        help="set the logging level (default: INFO)")
    args = parser.parse_args()

    log_level = getattr(logging, args.log.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log}")
    logging.basicConfig(level=log_level, format="%(message)s")

    LOGGER.debug("starting")

    all_declared_vars = find_unused_vars(args.directory)

    LOGGER.debug("\n **unused vars** \n")
    if not all_declared_vars:
        LOGGER.info("no unused vars")
    # filter out vars only declared in galaxy_roles and collections
    for var_name, var_locations in all_declared_vars.items():
        LOGGER.info(f"{var_name} at {var_locations}\n")

    LOGGER.debug("finished")


if __name__ == "__main__":
    main()
