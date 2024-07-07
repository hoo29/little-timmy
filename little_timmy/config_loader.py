import logging
import os
import yaml

from dataclasses import dataclass
from jsonschema import validate


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_FILE_NAME = ".little-timmy"
CONFIG_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "skip_vars": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "default": []
        }
    },
    "additionalProperties": False
}


@dataclass
class Config():
    skip_vars: set[str]


def load_config(path: str) -> Config:
    if path:
        with open(path, "r") as f:
            config = yaml.safe_load(f)
            if not config:
                config = {}
            validate(config, CONFIG_FILE_SCHEMA)
    else:
        config = {}

    if "skip_vars" not in config:
        config["skip_vars"] = []
    config["skip_vars"] = set(config["skip_vars"])
    return Config(**config)


def find_and_load_config(root_dir: str, absolute_path: str = "") -> Config:
    if absolute_path:
        LOGGER.debug(f"loading absolute config file {absolute_path}")
        return load_config(absolute_path)

    parts = os.path.split(root_dir)
    while parts[1]:
        full_config_path = os.path.join(*parts, DEFAULT_CONFIG_FILE_NAME)
        if os.path.isfile(full_config_path):
            LOGGER.debug(f"loading found config file {absolute_path}")
            return load_config(full_config_path)
        parts = os.path.split(parts[0])

    LOGGER.debug("loading default config file")
    return load_config("")
