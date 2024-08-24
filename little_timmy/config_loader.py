import logging
import os
import yaml

from dataclasses import dataclass
from jsonschema import validate


LOGGER = logging.getLogger("little-timmy")
DEFAULT_CONFIG_FILE_NAME = ".little-timmy"
CONFIG_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "skip_vars": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "skip_dirs": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "additionalProperties": False
}
CONFIG_FILE_DEFAULTS = {
    "skip_vars": [],
    "skip_dirs": ["molecule", "venv", "tests"]
}


@dataclass
class Config():
    skip_vars: list[str]
    skip_dirs: list[str]


def load_config(path: str) -> Config:
    if path:
        with open(path, "r") as f:
            config = yaml.safe_load(f)
            if not config:
                config = {}
    else:
        config = {}
    validate(config, CONFIG_FILE_SCHEMA)

    for k, v in CONFIG_FILE_DEFAULTS.items():
        if k not in config:
            config[k] = v
    return Config(**config)


def find_and_load_config(root_dir: str, absolute_path: str = "") -> Config:
    if absolute_path:
        LOGGER.debug(f"loading absolute config file {absolute_path}")
        return load_config(absolute_path)

    parts = os.path.split(root_dir)
    while parts[1]:
        full_config_path = os.path.join(*parts, DEFAULT_CONFIG_FILE_NAME)
        if os.path.isfile(full_config_path):
            LOGGER.debug(f"loading found config file {full_config_path}")
            return load_config(full_config_path)
        parts = os.path.split(parts[0])

    LOGGER.debug("loading default config file")
    return load_config("")
