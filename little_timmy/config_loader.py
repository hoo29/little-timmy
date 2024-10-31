import logging
import os
import yaml

from dataclasses import dataclass
from jinja2 import Environment
from jsonschema import validate


LOGGER = logging.getLogger("little-timmy")

DEFAULT_CONFIG_FILE_NAME = ".little-timmy"
DEFAULT_JINJA_CONTEXT_KEYS = [
    "assert.that",
    "changed_when",
    "debug.var",
    "failed_when",
    "until",
    "when",
]

# Taken from ansible.constants.INTERNAL_STATIC_VARS.
# Using ansible.constants.INTERNAL_STATIC_VARS directly didn't work across all tested python versions
DEFAULT_MAGIC_VARS = [
    "ansible_async_path",
    "ansible_collection_name",
    "ansible_config_file",
    "ansible_dependent_role_names",
    "ansible_diff_mode",
    "ansible_config_file",
    "ansible_facts",
    "ansible_forks",
    "ansible_inventory_sources",
    "ansible_limit",
    "ansible_play_batch",
    "ansible_play_hosts",
    "ansible_play_hosts_all",
    "ansible_play_role_names",
    "ansible_playbook_python",
    "ansible_role_name",
    "ansible_role_names",
    "ansible_run_tags",
    "ansible_skip_tags",
    "ansible_verbosity",
    "ansible_version",
    "inventory_dir",
    "inventory_file",
    "inventory_hostname",
    "inventory_hostname_short",
    "groups",
    "group_names",
    "omit",
    "hostvars",
    "playbook_dir",
    "play_hosts",
    "role_name",
    "role_names",
    "role_path",
    "role_uuid",
    "role_names",
]

CONFIG_FILE_DEFAULTS = {
    "extra_jinja_context_keys": [],
    "galaxy_dirs": ["ansible_collections", "galaxy_roles"],
    "skip_vars": [],
    "skip_dirs": ["molecule", "venv", "tests"],
}
CONFIG_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "galaxy_dirs": {
            "description": "Directories where ansible-galaxy collections and roles have been installed. Must be within the directory being scanned.",
            "default": ["ansible_collections", "galaxy_roles"],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "skip_vars": {
            "description": "Variables to skip checking.",
            "default": [],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "skip_dirs": {
            "description": "Directories to skip loading files from.",
            "default": ["molecule", "venv", "tests"],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "extra_jinja_context_keys": {
            "description": """
            Locations where there is already a jinja context for evaluation e.g. `when` and `assert.that`.
            Does not require module FQCN. Values are added to .config_loader.DEFAULT_JINJA_CONTEXT_KEYS.
            """,
            "default": [],
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "additionalProperties": False
}


@dataclass
class Config():
    galaxy_dirs: list[str]
    skip_vars: list[str]
    skip_dirs: list[str]
    jinja_context_keys: tuple[str]
    magic_vars: list[str]
    dirs_not_to_delcare_vars_from: list[str]


@dataclass
class Context():
    all_declared_vars: dict[str, set[str]]
    all_referenced_vars: dict[str, set[str]]
    config: Config
    jinja_env: Environment
    root_dir: str


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

    config["magic_vars"] = DEFAULT_MAGIC_VARS
    config["jinja_context_keys"] = tuple(
        config["extra_jinja_context_keys"] + DEFAULT_JINJA_CONTEXT_KEYS)
    config.pop("extra_jinja_context_keys", None)
    config["dirs_not_to_delcare_vars_from"] = config["galaxy_dirs"] + ["molecule"]
    return Config(**config)


def find_and_load_config(root_dir: str, absolute_path: str = "") -> Config:
    if absolute_path:
        LOGGER.debug(f"loading absolute config file {absolute_path}")
        return load_config(absolute_path)

    parts = os.path.split(root_dir)

    while parts[1]:
        full_config_path = os.path.join(*parts, DEFAULT_CONFIG_FILE_NAME)
        LOGGER.debug(f"looking for config file at {full_config_path}")
        if os.path.isfile(full_config_path):
            LOGGER.debug(f"loading found config file {full_config_path}")
            return load_config(full_config_path)
        parts = os.path.split(parts[0])

    LOGGER.debug("loading default config file")
    return load_config("")
