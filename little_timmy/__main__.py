from ansible import cli
from ansible import constants as C
from ansible_collections.ansible.utils.plugins.filter.ipaddr import FilterModule as UtilsIpAddrFilters
from ansible_collections.community.general.plugins.filter.lists import FilterModule as ListsFilters
from ansible_collections.community.general.plugins.filter.lists_mergeby import FilterModule as ListsMergeByFilters
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.filter.core import FilterModule as CoreFilters
from ansible.plugins.filter.mathstuff import FilterModule as MathFilters
from ansible.plugins.filter.urls import FilterModule as UrlsFilters
from ansible.plugins.filter.urlsplit import FilterModule as UrlSplitFilters
from ansible.plugins.loader import init_plugin_loader
from ansible.plugins.test.core import TestModule as CoreTests
from glob import iglob
from jinja2 import Environment, meta

import argparse
import os

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
    "ansible_skip_tags",
    "ansible_ssh_common_args",
    "ansible_ssh_use_tty",
    "ansible_user",
    "ansible_verbosity",
    "ansible_version",
    "group_names",
    "groups",
    "groups",
    "hostvars"
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
    "undef"
    "undefined",
}

YAML_FILE_EXTENSION_GLOB = "*y*ml"
EXTERNAL_DEP_DIRS = ["galaxy_roles", "ansible_collections"]
GLOBAL_DIRS_TO_EXCLUDE = ["molecule", "venv", "tests"]

# there must be a better way to do this
JINJA_ENV = Environment()
core_tests = CoreTests().tests()
JINJA_ENV.tests.update(core_tests)
filter_modules = {
    "ansible.builtin.core": [CoreFilters, UrlsFilters, UrlSplitFilters, MathFilters],
    "ansible.utils": [UtilsIpAddrFilters],
    "community.general": [ListsFilters, ListsMergeByFilters],
}
for fqdn, modules in filter_modules.items():
    for module in modules:
        for name, filter_func in module().filters().items():
            JINJA_ENV.filters[f"{fqdn}.{name}"] = filter_func
            JINJA_ENV.filters[name] = filter_func


def get_files_in_folder(root_dir: str, folder: str, file_glob: str = "*", include_ext=False, dirs_to_exclude: list[str] = []):
    if not include_ext:
        dirs_to_exclude = dirs_to_exclude + EXTERNAL_DEP_DIRS
    dirs_to_exclude = dirs_to_exclude + GLOBAL_DIRS_TO_EXCLUDE

    def should_exclude(path: str):
        relative_path = os.path.dirname(os.path.relpath(path, root_dir))
        return any(excluded_dir in relative_path for excluded_dir in dirs_to_exclude)

    return (
        f for f in iglob(f"{root_dir}/{folder}/**/{file_glob}", recursive=True)
        if os.path.isfile(f)
        and not should_exclude(f)
    )


def parse_jinja(value: any, all_referenced_vars: dict[str, set[str]], source: str):
    parsed = JINJA_ENV.parse(value)
    referenced_vars = meta.find_undeclared_variables(parsed)
    for referenced_var in referenced_vars:
        existing = all_referenced_vars.get(referenced_var, set())
        existing.add(source)
        all_referenced_vars[referenced_var] = existing


def parse_variable(var_name: str, var_value: any, all_declared_vars: dict[str, set[str]], all_referenced_vars: dict[str, set[str]], source: str, root_dir: str):
    if var_name in MAGIC_VAR_NAMES:
        return
    relative_path = os.path.dirname(os.path.relpath(source, root_dir))
    external = any(
        excluded_dir in relative_path for excluded_dir in EXTERNAL_DEP_DIRS)
    if not external:
        existing = all_declared_vars.get(var_name, set())
        existing.add(source)
        all_declared_vars[var_name] = existing
    parse_jinja(var_value, all_referenced_vars, source)


def check_raw_file_for_variables(value: str, all_declared_vars: dict[str, set[str]], all_referenced_vars: dict[str, set[str]], source: str):
    for var_name in all_declared_vars.keys():
        if var_name in value:
            existing = all_referenced_vars.get(var_name, set())
            existing.add(source)
            all_referenced_vars[var_name] = existing


def main():
    parser = argparse.ArgumentParser(description="Process a directory path.")
    parser.add_argument("directory", nargs="?", default=".",
                        type=str, help="The directory to process")
    args = parser.parse_args()
    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"{directory} does not exist.")
        exit(1)

    if directory.endswith("/"):
        directory = directory[:-1]

    all_declared_vars: dict[str, set[str]] = {}
    all_referenced_vars: dict[str, set[str]] = {}

    init_plugin_loader()
    # Setup dataloader and vault
    loader = DataLoader()
    vault_ids = C.DEFAULT_VAULT_IDENTITY_LIST
    vault_secrets = cli.CLI.setup_vault_secrets(loader, vault_ids=vault_ids)
    loader.set_vault_secrets(vault_secrets)

    # Process all the things

    # group_vars
    for path in get_files_in_folder(directory, "**/group_vars", YAML_FILE_EXTENSION_GLOB):
        print(f"group_var {path}")

        contents = loader.load_from_file(path) or {}
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value,
                           all_declared_vars, all_referenced_vars, path, directory)

    # host_vars
    for path in get_files_in_folder(directory, "**/host_vars", YAML_FILE_EXTENSION_GLOB):
        print(f"host_var {path}")
        contents = loader.load_from_file(path) or {}
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value,
                           all_declared_vars, all_referenced_vars, path, directory)
    # vars
    for path in get_files_in_folder(directory, "**/vars", YAML_FILE_EXTENSION_GLOB, include_ext=True):
        print(f"var file {path}")
        contents = loader.load_from_file(path) or {}
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value,
                           all_declared_vars, all_referenced_vars, path, directory)

    # defaults
    for path in get_files_in_folder(directory, "**/defaults", YAML_FILE_EXTENSION_GLOB, include_ext=True):
        print(f"default {path}")
        contents = loader.load_from_file(path) or {}
        for var_name, var_value in contents.items():
            parse_variable(var_name, var_value,
                           all_declared_vars, all_referenced_vars, path, directory)

    # inventory
    for inv_folder in ["inventory", "inventories"]:
        for path in get_files_in_folder(directory, inv_folder, dirs_to_exclude=["group_vars", "host_vars"]):
            print(f"inv file {path}")
            inventory = InventoryManager(loader=loader, sources=path)
            # groups
            for _, group_value in inventory.groups.items():
                # vars in group
                for var_name, var_value in group_value.vars.items():
                    parse_variable(var_name, var_value,
                                   all_declared_vars, all_referenced_vars, path, directory)
                # hosts in group
                for host in group_value.hosts:
                    # vars in host
                    for var_name, var_value in host.vars.items():
                        parse_variable(var_name, var_value,
                                       all_declared_vars, all_referenced_vars, path, directory)

    # templates
    for path in get_files_in_folder(directory, "**/templates", include_ext=True):
        print(f"template file {path}")
        with open(path, "r") as f:
            parse_jinja(f.read(), all_referenced_vars, path)

    # playbook in current directory
    for path in iglob(f"{directory}/playbook*{YAML_FILE_EXTENSION_GLOB}", recursive=False):
        print(f"playbook {path}")
        with open(path, "r") as f:
            check_raw_file_for_variables(
                f.read(), all_declared_vars, all_referenced_vars, path)

    # tasks files
    for path in get_files_in_folder(directory, "**/tasks", YAML_FILE_EXTENSION_GLOB, True):
        print(f"task file {path}")
        with open(path, "r") as f:
            check_raw_file_for_variables(
                f.read(), all_declared_vars, all_referenced_vars, path)

    # handlers files
    for path in get_files_in_folder(directory, "**/handlers", YAML_FILE_EXTENSION_GLOB, True):
        print(f"handler file {path}")
        with open(path, "r") as f:
            check_raw_file_for_variables(
                f.read(), all_declared_vars, all_referenced_vars, path)

    for var_name in all_referenced_vars.keys():
        print(f"removing referenced var {var_name}")
        all_declared_vars.pop(var_name, None)

    print("\n **unused vars** \n")
    # filter out vars only declared in galaxy_roles and collections
    for var_name, var_locations in all_declared_vars.items():
        print(f"{var_name} at {var_locations}\n")


if __name__ == "__main__":
    main()
