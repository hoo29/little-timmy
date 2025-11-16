import logging
import os
import sys
import types
import yaml
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment
from jsonschema import validate
from ansible import cli, constants as C
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.filter import AnsibleJinja2Filter
try:
    # ansible >= 12 (ansible-core >= 2.19)
    from ansible._internal._templating._jinja_plugins import JinjaPluginIntercept
    from ansible.parsing.vault import VaultSecretsContext
    from jinja2 import defaults as jinja2_defaults
    ANSIBLE_12_PLUS = True
except ImportError:
    # ansible < 12 (ansible-core < 2.19)
    from ansible.template import JinjaPluginIntercept
    VaultSecretsContext = None
    jinja2_defaults = None
    ANSIBLE_12_PLUS = False
from ansible.plugins.loader import test_loader, Jinja2Loader, init_plugin_loader
import ansible_collections

from .utils import get_items_in_folder

# must be run only once
init_plugin_loader()

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
    "skip_vars_duplicates_substrings": ["pass", "vault"],
    "playbook_globs": ["/**/*playbook.y*ml"],
    "template_globs": ["/**/templates/**/*"]
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
        "skip_vars_duplicates_substrings": {
            "description": "Variables containing these substring will not be checked for duplication. This is in addition to skip_vars.",
            "default": ["pass", "vault"],
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
        "playbook_globs": {
            "description": "Globs where to find playbooks.",
            "default": ["/**/*playbook.y*ml"],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "template_globs": {
            "description": "Globs where to find temlates.",
            "default": ["/**/templates/**/*"],
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
    skip_vars_duplicates_substrings: list[str]
    skip_dirs: list[str]
    playbook_globs: list[str]
    template_globs: list[str]
    jinja_context_keys: tuple[str]
    magic_vars: list[str]
    dirs_not_to_delcare_vars_from: list[str]


class DuplicatedVarInfo():
    locations: set[str]
    original: str

    def __init__(self):
        self.locations = set()
        self.original = ""


@dataclass
class Context():
    all_declared_vars: dict[str, set[str]]
    all_duplicated_vars: dict[str, DuplicatedVarInfo]
    all_referenced_vars: dict[str, set[str]]
    all_unused_vars: dict[str, set[str]]
    config: Config
    loader: DataLoader
    jinja_env: Environment
    root_dir: str


def find_and_setup_galaxy_collections(root_dir: str, skip_dirs: list[str]) -> None:
    """
    Find all galaxy collections in the root directory and set them up for FQDN access.
    Creates in-memory Python modules without modifying the filesystem.
    """
    # Look for galaxy.yml files which indicate a collection
    galaxy_files = get_items_in_folder(
        root_dir, f"{root_dir}/**/galaxy.yml", skip_dirs, include_ext=True, dirs_to_exclude=skip_dirs
    )

    for galaxy_file in galaxy_files:
        collection_dir = Path(galaxy_file).parent

        # Read galaxy.yml to get namespace and name
        try:
            with open(galaxy_file, "r") as f:
                galaxy_info = yaml.safe_load(f)
        except Exception as e:
            LOGGER.debug(f"Error reading galaxy.yml at {galaxy_file}: {e}")
            continue

        namespace = galaxy_info.get("namespace")
        name = galaxy_info.get("name")

        if not namespace or not name:
            continue

        # Create in-memory Python modules for the collection
        # This avoids modifying the filesystem while still allowing FQDN resolution
        try:
            # Create collection metadata
            collection_meta = {
                "name": f"{namespace}.{name}",
                "version": galaxy_info.get("version", "1.0.0"),
                "authors": galaxy_info.get("authors", []),
                "description": galaxy_info.get("description", ""),
                "plugin_routing": {},
            }

            # Create collection module (skip if already exists)
            collection_module_name = f"ansible_collections.{namespace}.{name}"
            if collection_module_name in sys.modules:
                LOGGER.debug(
                    f"Collection {namespace}.{name} already registered")
                continue

            collection_module = types.ModuleType(collection_module_name)
            collection_module._collection_meta = collection_meta
            collection_module.__path__ = [str(collection_dir.resolve())]
            sys.modules[collection_module_name] = collection_module

            LOGGER.debug(f"Registered in-memory collection {namespace}.{name}")
        except Exception as e:
            LOGGER.debug(
                f"Error registering collection {namespace}.{name}: {e}")


def setup_run(root_dir: str, absolute_path: str = "") -> Context:

    if not os.path.isdir(root_dir):
        raise ValueError(f"{root_dir} does not exist")
    if root_dir.endswith("/"):
        root_dir = root_dir[:-1]

    config = find_and_load_config(root_dir, absolute_path)
    # Setup dataloader and vault
    loader = DataLoader()
    vault_ids = C.DEFAULT_VAULT_IDENTITY_LIST

    # In ansible >= 12, VaultSecretsContext can only be initialized once
    # Check if it's already initialized before calling setup_vault_secrets
    if VaultSecretsContext is not None and VaultSecretsContext.current(optional=True):
        # Already initialized, just get the secrets from the current context
        vault_secrets = VaultSecretsContext.current().secrets
    else:
        # Not initialized yet (or ansible < 12), initialize it
        vault_secrets = cli.CLI.setup_vault_secrets(
            loader, vault_ids=vault_ids)

    loader.set_vault_secrets(vault_secrets)

    # Find galaxy collections and register them in-memory for FQDN access
    # This allows FQDN filter names (e.g., namespace.collection.filter_name) to be resolved
    # without modifying the filesystem
    find_and_setup_galaxy_collections(root_dir, config.skip_dirs)

    # Setup jinja env
    plugin_folders = get_items_in_folder(
        root_dir, f"{root_dir}/**/filter_plugins", config.galaxy_dirs, True, config.skip_dirs, False)
    jinja_env = Environment()

    # Create filter plugin loader
    filter_loader = Jinja2Loader(
        'FilterModule',
        'ansible.plugins.filter',
        C.DEFAULT_FILTER_PLUGIN_PATH +
        [os.path.abspath(x) for x in plugin_folders],
        'filter_plugins',
        AnsibleJinja2Filter
    )

    # In ansible >= 12, JinjaPluginIntercept signature changed
    # Old: JinjaPluginIntercept(delegatee, pluginloader)
    # New: JinjaPluginIntercept(jinja_builtins, plugin_loader)
    # where jinja_builtins must be wrapped using loader._wrap_funcs
    # Note: _wrap_funcs is an internal method, but it's the standard way ansible
    # itself uses to create JinjaPluginIntercept instances (see ansible/_internal/_templating/_jinja_bits.py)
    if ANSIBLE_12_PLUS:
        # Use jinja2 defaults for builtins, wrapped by the loader
        builtin_filters = filter_loader._wrap_funcs(
            jinja2_defaults.DEFAULT_FILTERS, {})
        builtin_tests = test_loader._wrap_funcs(
            jinja2_defaults.DEFAULT_TESTS, {})
        jinja_env.filters = JinjaPluginIntercept(
            builtin_filters, filter_loader)
        jinja_env.tests = JinjaPluginIntercept(builtin_tests, test_loader)
    else:
        # Use jinja_env's own filters/tests as delegatee
        jinja_env.filters = JinjaPluginIntercept(
            jinja_env.filters, filter_loader)
        jinja_env.tests = JinjaPluginIntercept(jinja_env.tests, test_loader)

    # Setup context
    all_declared_vars: dict[str, set[str]] = defaultdict(set)
    all_referenced_vars: dict[str, set[str]] = defaultdict(set)
    all_duplicated_vars: dict[str, DuplicatedVarInfo] = defaultdict(
        DuplicatedVarInfo)
    all_unused_vars: dict[str, set[str]] = defaultdict(set)
    return Context(
        all_declared_vars,
        all_duplicated_vars,
        all_referenced_vars,
        all_unused_vars,
        config,
        loader,
        jinja_env,
        root_dir,
    )


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
