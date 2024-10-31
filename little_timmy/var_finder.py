import logging
import os


from ansible import cli, constants as C
from ansible.errors import AnsibleParserError
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import AnsibleVaultError, AnsibleVaultFormatError, AnsibleVaultPasswordError
from ansible.plugins.filter import AnsibleJinja2Filter
from ansible.plugins.loader import init_plugin_loader, test_loader, Jinja2Loader
from ansible.template import JinjaPluginIntercept
from collections import defaultdict
from glob import iglob
from jinja2 import Environment

from .config_loader import Config, Context
from .taml import parse_jinja, parse_yaml_list, parse_yaml_variable

YAML_FILE_EXTENSION_GLOB = "*y*ml"
LOGGER = logging.getLogger("little-timmy")

# must be run only once
init_plugin_loader()


def get_items_in_folder(root_dir: str, search_glob: str, galaxy_dirs: list[str], include_ext=False, dirs_to_exclude: list[str] = [], files=True):
    if not include_ext:
        dirs_to_exclude = dirs_to_exclude + galaxy_dirs

    def should_exclude(path: str):
        relative_path = os.path.dirname(os.path.relpath(path, root_dir))
        return any(excluded_dir in relative_path for excluded_dir in dirs_to_exclude)

    return (
        os.path.abspath(f) for f in iglob(search_glob, recursive=True)
        if ((files and os.path.isfile(f)) or (not files and os.path.isdir(f)))
        and not should_exclude(f)
    )


def load_data_from_file(path: str, loader: DataLoader):
    try:
        return loader.load_from_file(path) or {}
    except (AnsibleVaultError or AnsibleVaultFormatError or AnsibleVaultPasswordError) as err:
        raise ValueError(f"Ansible vault error for file {path}") from err
    except AnsibleParserError as err:
        raise ValueError(f"Ansible parse error for file {path}") from err


def find_unused_vars(directory: str, config: Config) -> dict[str, set[str]]:
    if not os.path.isdir(directory):
        raise ValueError(f"{directory} does not exist")
    if directory.endswith("/"):
        directory = directory[:-1]

    # Setup dataloader and vault
    loader = DataLoader()
    vault_ids = C.DEFAULT_VAULT_IDENTITY_LIST
    vault_secrets = cli.CLI.setup_vault_secrets(loader, vault_ids=vault_ids)
    loader.set_vault_secrets(vault_secrets)
    # Setup jinja env
    plugin_folders = get_items_in_folder(
        directory,  f"{directory}/**/filter_plugins", config.galaxy_dirs, True, config.skip_dirs, False)
    jinja_env = Environment()
    jinja_env.filters = JinjaPluginIntercept(jinja_env.filters, Jinja2Loader(
        'FilterModule',
        'ansible.plugins.filter',
        C.DEFAULT_FILTER_PLUGIN_PATH +
        [os.path.abspath(x) for x in plugin_folders],
        'filter_plugins',
        AnsibleJinja2Filter
    ))
    jinja_env.tests = JinjaPluginIntercept(jinja_env.tests, test_loader)

    # Setup context
    all_declared_vars: dict[str, set[str]] = defaultdict(set)
    all_referenced_vars: dict[str, set[str]] = defaultdict(set)
    context = Context(
        all_declared_vars,
        all_referenced_vars,
        config,
        jinja_env,
        directory
    )

    # Process all the things

    # group_vars
    for path in get_items_in_folder(directory, f"{directory}/**/group_vars/**/{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs, dirs_to_exclude=config.skip_dirs):
        LOGGER.debug(f"group_var {path}")

        contents = load_data_from_file(path, loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # host_vars
    for path in get_items_in_folder(directory, f"{directory}/**/host_vars/**/{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs, dirs_to_exclude=config.skip_dirs):
        LOGGER.debug(f"host_var {path}")
        contents = load_data_from_file(path, loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # vars
    for path in get_items_in_folder(directory, f"{directory}/**/vars/**/{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs, include_ext=True, dirs_to_exclude=config.skip_dirs):
        LOGGER.debug(f"var file {path}")
        contents = load_data_from_file(path, loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # defaults
    for path in get_items_in_folder(directory, f"{directory}/**/defaults/**/{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs, include_ext=True, dirs_to_exclude=config.skip_dirs):
        # exclude
        LOGGER.debug(f"default {path}")
        contents = load_data_from_file(path, loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # inventory
    for inv_folder in ["inventory", "inventories"]:
        for path in get_items_in_folder(directory, f"{directory}/{inv_folder}/**/*",
                                        config.galaxy_dirs, dirs_to_exclude=config.skip_dirs + ["group_vars", "host_vars", "files", "templates"]):
            LOGGER.debug(f"inv file {path}")
            inventory = InventoryManager(loader=loader, sources=path)
            # groups
            for _, group_value in inventory.groups.items():
                # vars in group
                for var_name, var_value in group_value.vars.items():
                    parse_yaml_variable(var_name, var_value, path, context)
                # hosts in group
                for host in group_value.hosts:
                    # vars in host
                    for var_name, var_value in host.vars.items():
                        parse_yaml_variable(
                            var_name, var_value, path, context)

    # playbooks
    for path in get_items_in_folder(directory,  f"{directory}/**/*playbook{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs, dirs_to_exclude=config.skip_dirs):
        LOGGER.debug(f"playbook {path}")
        contents = load_data_from_file(path, loader)
        parse_yaml_list(contents, path, context)

    # tasks files
    for path in get_items_in_folder(directory, f"{directory}/**/tasks/**/{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs, True, dirs_to_exclude=config.skip_dirs):
        LOGGER.debug(f"task file {path}")
        contents = load_data_from_file(path, loader)
        parse_yaml_list(contents, path, context)

    # handlers files
    for path in get_items_in_folder(directory, f"{directory}/**/handlers/**/{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs, True, dirs_to_exclude=config.skip_dirs):
        LOGGER.debug(f"handler file {path}")
        contents = load_data_from_file(path, loader)
        parse_yaml_list(contents, path, context)

    # templates
    for path in get_items_in_folder(directory, f"{directory}/**/templates/**/*",
                                    config.galaxy_dirs, True, dirs_to_exclude=config.skip_dirs):
        LOGGER.debug(f"template file {path}")
        with open(path, "r") as f:
            parse_jinja(f.read(), path, context)

    # check local molecule folder for variable consumption only
    for path in get_items_in_folder(directory, f"{directory}/molecule/**/{YAML_FILE_EXTENSION_GLOB}",
                                    config.galaxy_dirs):
        LOGGER.debug(f"molecule file {path}")
        contents = load_data_from_file(path, loader)
        parse_yaml_list(contents, path, context)

    for var_name in all_referenced_vars.keys():
        all_declared_vars.pop(var_name, None)

    return all_declared_vars
