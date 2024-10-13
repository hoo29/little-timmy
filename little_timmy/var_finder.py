import logging
import os
import re

from ansible import cli, constants as C
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import AnsibleVaultError, AnsibleVaultFormatError, AnsibleVaultPasswordError
from ansible.plugins.loader import init_plugin_loader, filter_loader, test_loader
from ansible.template import JinjaPluginIntercept
from dataclasses import dataclass
from glob import iglob
from jinja2 import Environment, exceptions, meta
from typing import Any

from .config_loader import Config

MAGIC_VAR_NAMES = {
    "ansible_become_user",
    "ansible_check_mode",
    "ansible_collection_name",
    "ansible_config_file",
    "ansible_connection",
    "ansible_dependent_role_names",
    "ansible_diff_mode",
    "ansible_facts",
    "ansible_forks",
    "ansible_host",
    "ansible_host",
    "ansible_index_var",
    "ansible_inventory_sources",
    "ansible_limit",
    "ansible_local",
    "ansible_loop_var",
    "ansible_loop",
    "ansible_parent_role_names",
    "ansible_parent_role_paths",
    "ansible_play_batch",
    "ansible_play_hosts_all",
    "ansible_play_hosts",
    "ansible_play_name",
    "ansible_play_role_names",
    "ansible_playbook_python",
    "ansible_python_interpreter",
    "ansible_role_name",
    "ansible_role_names",
    "ansible_run_tags",
    "ansible_search_path",
    "ansible_shell_type",
    "ansible_skip_tags",
    "ansible_ssh_common_args",
    "ansible_ssh_transfer_method",
    "ansible_ssh_use_tty",
    "ansible_user",
    "ansible_verbosity",
    "ansible_version",
    "group_names",
    "groups",
    "hostvars",
    "inventory_dir",
    "inventory_file",
    "inventory_hostname_short",
    "inventory_hostname",
    "omit",
    "play_hosts",
    "playbook_dir",
    "role_name",
    "role_names",
    "role_path",
    "undef",
    "undefined",
}
YAML_FILE_EXTENSION_GLOB = "*y*ml"
EXTERNAL_DEP_DIRS = ["galaxy_roles", "ansible_collections"]

JINJA_ENV = Environment()
JINJA_ENV.filters = JinjaPluginIntercept(JINJA_ENV.filters, filter_loader)
JINJA_ENV.tests = JinjaPluginIntercept(JINJA_ENV.tests, test_loader)

LOGGER = logging.getLogger("little-timmy")

# must be run only once
init_plugin_loader()


@dataclass
class Context():
    all_declared_vars: dict[str, set[str]]
    all_referenced_vars: dict[str, set[str]]
    config: Config
    root_dir: str
    complied_regex: dict[str, Any]


def get_files_in_folder(root_dir: str, folder: str, config: Config, file_glob: str = "*", include_ext=False, dirs_to_exclude: list[str] = []):
    if not include_ext:
        dirs_to_exclude = dirs_to_exclude + EXTERNAL_DEP_DIRS
    dirs_to_exclude = dirs_to_exclude + config.skip_dirs

    def should_exclude(path: str):
        relative_path = os.path.dirname(os.path.relpath(path, root_dir))
        return any(excluded_dir in relative_path for excluded_dir in dirs_to_exclude)

    return (
        f for f in iglob(f"{root_dir}/{folder}/**/{file_glob}", recursive=True)
        if os.path.isfile(f)
        and not should_exclude(f)
    )


def parse_jinja(value: any, all_referenced_vars: dict[str, set[str]], source: str):
    try:
        parsed = JINJA_ENV.parse(value)
    except (AnsibleVaultError or AnsibleVaultFormatError or AnsibleVaultPasswordError) as err:
        raise ValueError(f"Ansible vault error for file {source}") from err
    referenced_vars = meta.find_undeclared_variables(parsed)
    for referenced_var in referenced_vars:
        existing = all_referenced_vars.get(referenced_var, set())
        existing.add(source)
        all_referenced_vars[referenced_var] = existing


def parse_variable(var_name: str, var_value: any, source: str, context: Context):
    if var_name in MAGIC_VAR_NAMES or var_name in context.config.skip_vars:
        return
    relative_path = os.path.dirname(os.path.relpath(source, context.root_dir))
    external = any(
        excluded_dir in relative_path for excluded_dir in EXTERNAL_DEP_DIRS)
    if not external:
        existing = context.all_declared_vars.get(var_name, set())
        existing.add(source)
        context.all_declared_vars[var_name] = existing
    parse_jinja(var_value, context.all_referenced_vars, source)


def check_raw_file_for_variables(value: str, source: str, context: Context):
    for var_name in context.all_declared_vars.keys():
        if re.search(context.complied_regex[var_name], value):
            existing = context.all_referenced_vars.get(var_name, set())
            existing.add(source)
            context.all_referenced_vars[var_name] = existing


def load_data_from_file(path: str, loader: DataLoader):
    try:
        return loader.load_from_file(path) or {}
    except (AnsibleVaultError or AnsibleVaultFormatError or AnsibleVaultPasswordError) as err:
        raise ValueError(f"Ansible vault error for file {path}") from err


def find_unused_vars(directory: str, config: Config) -> dict[str, set[str]]:
    if not os.path.isdir(directory):
        raise ValueError(f"{directory} does not exist.")
    if directory.endswith("/"):
        directory = directory[:-1]

    all_declared_vars: dict[str, set[str]] = {}
    all_referenced_vars: dict[str, set[str]] = {}
    complied_regex: dict[str, Any] = {}
    context = Context(
        all_declared_vars,
        all_referenced_vars,
        config,
        directory,
        complied_regex
    )

    # Setup dataloader and vault
    loader = DataLoader()
    vault_ids = C.DEFAULT_VAULT_IDENTITY_LIST
    vault_secrets = cli.CLI.setup_vault_secrets(loader, vault_ids=vault_ids)
    loader.set_vault_secrets(vault_secrets)
    # Process all the things

    # Load things that declare vars

    # group_vars
    for path in get_files_in_folder(directory, "**/group_vars", config, YAML_FILE_EXTENSION_GLOB):
        LOGGER.debug(f"group_var {path}")

        contents = load_data_from_file(path, loader)
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value, path, context)

    # host_vars
    for path in get_files_in_folder(directory, "**/host_vars", config, YAML_FILE_EXTENSION_GLOB):
        LOGGER.debug(f"host_var {path}")
        contents = load_data_from_file(path, loader)
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value, path, context)
    # vars
    for path in get_files_in_folder(directory, "**/vars", config, YAML_FILE_EXTENSION_GLOB, include_ext=True):
        LOGGER.debug(f"var file {path}")
        contents = load_data_from_file(path, loader)
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value, path, context)

    # defaults
    for path in get_files_in_folder(directory, "**/defaults", config, YAML_FILE_EXTENSION_GLOB, include_ext=True):
        LOGGER.debug(f"default {path}")
        contents = load_data_from_file(path, loader)
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value, path, context)

    # inventory
    for inv_folder in ["inventory", "inventories"]:
        for path in get_files_in_folder(directory, inv_folder, config, dirs_to_exclude=["group_vars", "host_vars", "files"]):
            LOGGER.debug(f"inv file {path}")
            inventory = InventoryManager(loader=loader, sources=path)
            # groups
            for _, group_value in inventory.groups.items():
                # vars in group
                for var_name, var_value in group_value.vars.items():
                    parse_variable(var_name, var_value, path, context)
                # hosts in group
                for host in group_value.hosts:
                    # vars in host
                    for var_name, var_value in host.vars.items():
                        parse_variable(var_name, var_value, path, context)

    for var in context.all_declared_vars.keys():
        context.complied_regex[var] = re.compile(fr"\b{re.escape(var)}\b")

    # Load things that consume vars

    # templates
    for path in get_files_in_folder(directory, "**/templates", config, include_ext=True):
        LOGGER.debug(f"template file {path}")
        with open(path, "r") as f:
            contents = f.read()
            try:
                parse_jinja(contents, all_referenced_vars, path)
            except exceptions.TemplateSyntaxError:
                check_raw_file_for_variables(contents, path, context)

    # playbooks
    for path in get_files_in_folder(directory, ".", config, f"*playbook*{YAML_FILE_EXTENSION_GLOB}"):
        LOGGER.debug(f"playbook {path}")
        with open(path, "r") as f:
            check_raw_file_for_variables(f.read(), path, context)

    # tasks files
    for path in get_files_in_folder(directory, "**/tasks", config, YAML_FILE_EXTENSION_GLOB, True):
        LOGGER.debug(f"task file {path}")
        with open(path, "r") as f:
            check_raw_file_for_variables(f.read(), path, context)

    # handlers files
    for path in get_files_in_folder(directory, "**/handlers", config, YAML_FILE_EXTENSION_GLOB, True):
        LOGGER.debug(f"handler file {path}")
        with open(path, "r") as f:
            check_raw_file_for_variables(f.read(), path, context)

    for var_name in all_referenced_vars.keys():
        LOGGER.debug(f"removing referenced var {var_name}")
        all_declared_vars.pop(var_name, None)

    return all_declared_vars
