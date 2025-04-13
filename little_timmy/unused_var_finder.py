import logging
import os

from ansible.inventory.manager import InventoryManager

from .config_loader import Context
from .taml import parse_jinja, parse_yaml_list, parse_yaml_variable
from .utils import get_items_in_folder, load_data_from_file, get_inventories

YAML_FILE_EXTENSION_GLOB = "*y*ml"
LOGGER = logging.getLogger("little-timmy")


def find_unused_vars(context: Context) -> dict[str, set[str]]:
    LOGGER.debug(f"find unused vars")
    # Process all the things
    # group_vars
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/group_vars/**/{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs, dirs_to_exclude=context.config.skip_dirs):
        LOGGER.debug(f"group_var {path}")

        contents = load_data_from_file(path, context.loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # host_vars
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/host_vars/**/{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs, dirs_to_exclude=context.config.skip_dirs):
        LOGGER.debug(f"host_var {path}")
        contents = load_data_from_file(path, context.loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # vars
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/vars/**/{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs, include_ext=True, dirs_to_exclude=context.config.skip_dirs):
        LOGGER.debug(f"var file {path}")
        contents = load_data_from_file(path, context.loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # defaults
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/defaults/**/{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs, include_ext=True, dirs_to_exclude=context.config.skip_dirs):
        # exclude
        LOGGER.debug(f"default {path}")
        contents = load_data_from_file(path, context.loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            parse_yaml_variable(var_name, var_value, path, context)

    # inventory
    for path in get_inventories(context.root_dir, context.config.galaxy_dirs, context.config.skip_dirs):
        LOGGER.debug(f"inv file {path}")
        if "dynamic" in os.path.basename(path):
            LOGGER.debug(f"skipping dynamic inventory file {path}")
            continue
        inventory = InventoryManager(loader=context.loader, sources=path)
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
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/*playbook{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs, dirs_to_exclude=context.config.skip_dirs):
        LOGGER.debug(f"playbook {path}")
        contents = load_data_from_file(path, context.loader)
        parse_yaml_list(contents, path, context)

    # tasks files
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/tasks/**/{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs, True, dirs_to_exclude=context.config.skip_dirs):
        LOGGER.debug(f"task file {path}")
        contents = load_data_from_file(path, context.loader)
        parse_yaml_list(contents, path, context)

    # handlers files
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/handlers/**/{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs, True, dirs_to_exclude=context.config.skip_dirs):
        LOGGER.debug(f"handler file {path}")
        contents = load_data_from_file(path, context.loader)
        parse_yaml_list(contents, path, context)

    # templates
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/**/templates/**/*",
                                    context.config.galaxy_dirs, True, dirs_to_exclude=context.config.skip_dirs):
        LOGGER.debug(f"template file {path}")
        with open(path, "r") as f:
            parse_jinja(f.read(), path, context)

    # check local molecule folder for variable consumption only
    for path in get_items_in_folder(context.root_dir, f"{context.root_dir}/molecule/**/{YAML_FILE_EXTENSION_GLOB}",
                                    context.config.galaxy_dirs):
        LOGGER.debug(f"molecule file {path}")
        contents = load_data_from_file(path, context.loader)
        parse_yaml_list(contents, path, context)

    for var_name in context.all_declared_vars.keys():
        if var_name not in context.all_referenced_vars.keys():
            context.all_unused_vars[var_name].update(
                context.all_declared_vars[var_name])
