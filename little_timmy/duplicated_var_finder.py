from collections import defaultdict
import logging
import os

from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode
from ansible.inventory.manager import InventoryManager
from ansible.inventory.helpers import sort_groups

from .config_loader import Context
from .utils import get_inventories, load_data_from_file, skip_var

LOGGER = logging.getLogger("little-timmy")


class VariableValueDetails():
    value: str
    level: int
    path: str

    def __init__(self, value: str, level: int, path: str):
        self.value = value
        self.level = level
        self.path = path


def check_var_for_duplication(var_name: str, var_value: str, host_name: str, path: str, level: int, vars_for_host: dict[str, list[VariableValueDetails]], context: Context):
    if skip_var(var_name, context.config.magic_vars, context.config.skip_vars) or any([x for x in context.config.skip_vars_duplicates_substrings if x in var_name]):
        return

    # In python 3.9 sometimes these are bytes?
    if isinstance(path, bytes):
        path = path.decode('utf-8')

    # These may appear in plain in logs if we use the standard value
    if isinstance(var_value, AnsibleVaultEncryptedUnicode):
        try:
            # wrap in try catch as we are accessing a hidden field
            var_value = var_value._ciphertext
        except:
            LOGGER.debug(
                f"failed to parse to get cipher text for {var_name} at {path}")
            return

    last_value = vars_for_host[var_name][-1] if vars_for_host[var_name] else None
    if last_value:

        if last_value.level < level and last_value.value != var_value:
            vars_for_host[var_name].append(
                VariableValueDetails(var_value, level, path))
        else:
            key = f"{host_name}##{var_name}##{var_value}"
            context.all_duplicated_vars[key].locations.add(path)
            context.all_duplicated_vars[key].original = last_value.path
    else:
        vars_for_host[var_name].append(
            VariableValueDetails(var_value, level, path))


def check_entity_for_duplicates(base_path: str, entity_type: str, entity: str, host_name: str, level: int, vars_for_host: dict[str, list[VariableValueDetails]], context: Context):

    files = context.loader.find_vars_files(
        os.path.join(base_path, entity_type), entity)
    for f in files:
        contents = load_data_from_file(f, context.loader)
        if not isinstance(contents, dict):
            continue
        for var_name, var_value in contents.items():
            check_var_for_duplication(
                var_name, var_value, host_name, f, level, vars_for_host, context)


def find_duplicated_vars(context: Context):
    LOGGER.debug(f"find duplicated vars")
    for inventory_path in get_inventories(context.root_dir, context.config.galaxy_dirs, context.config.skip_dirs):
        LOGGER.debug(f"inv file {inventory_path}")
        if "dynamic" in os.path.basename(inventory_path):
            LOGGER.debug(f"skipping dynamic inventory file {inventory_path}")
            continue

        inventory = InventoryManager(
            loader=context.loader, sources=inventory_path, cache=True)
        inventory_base_path = os.path.split(inventory_path)[0]

        for host in inventory.get_hosts():
            LOGGER.debug(f"host {host.name}")
            vars_for_host: dict[str,
                                list[VariableValueDetails]] = defaultdict(list)
            # remove all as we deal with it separately
            groups = sort_groups(host.groups)[1:]

            # 300 - inventory file or script group vars
            for group in sort_groups(inventory.groups.values()):
                for var_name, var_value in group.vars.items():
                    check_var_for_duplication(var_name, var_value,
                                              host.name, inventory_path, 300 + group.depth, vars_for_host, context)
            # 400 - inventory group_vars/all
            check_entity_for_duplicates(
                inventory_base_path, "group_vars", "all", host.name, 400, vars_for_host, context)
            # 500 - playbook group_vars/all
            check_entity_for_duplicates(
                context.root_dir, "group_vars", "all", host.name, 500, vars_for_host, context)
            # 600 - inventory group_vars/*
            for group in groups:
                check_entity_for_duplicates(
                    inventory_base_path, "group_vars", group.name, host.name, 600 + group.depth, vars_for_host, context)
            # 700 - playbook group_vars/*
            for group in groups:
                check_entity_for_duplicates(
                    context.root_dir, "group_vars", group.name, host.name, 700 + group.depth, vars_for_host, context)
            # 800 - inventory file or script host vars
            for var_name, var_value in host.vars.items():
                check_var_for_duplication(var_name, var_value,
                                          inventory_path, host.name, 800, vars_for_host, context)
            # 900 - inventory host_vars/*
            check_entity_for_duplicates(
                inventory_base_path, "host_vars", host.name, host.name, 900, vars_for_host, context)
            # 1000 - playbook host_vars/*
            check_entity_for_duplicates(
                context.root_dir, "host_vars", host.name, host.name, 1000, vars_for_host, context)
