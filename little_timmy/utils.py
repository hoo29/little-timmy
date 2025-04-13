import os

from ansible.errors import AnsibleParserError
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import AnsibleVaultError, AnsibleVaultFormatError, AnsibleVaultPasswordError
from glob import iglob

# The DataLoader cache is not working so use our own basic one
loader_cache = {}


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
        if path not in loader_cache:
            loader_cache[path] = loader.load_from_file(path) or {}
        return loader_cache[path]
    except (AnsibleVaultError or AnsibleVaultFormatError or AnsibleVaultPasswordError) as err:
        raise ValueError(f"Ansible vault error for file {path}") from err
    except AnsibleParserError as err:
        raise ValueError(f"Ansible parse error for file {path}") from err


def get_inventories(path: str, galaxy_dirs: list[str], skip_dirs: list[str]):
    for inv_folder in ["inventory", "inventories"]:
        for path in get_items_in_folder(path, f"{path}/{inv_folder}/**/*",
                                        galaxy_dirs, dirs_to_exclude=skip_dirs + ["group_vars", "host_vars", "files", "templates"]):
            yield path


def skip_var(var_name: str, magic_vars: list[str], skip_vars: list[str]):
    return (
        var_name.startswith("ansible_") or
        var_name in magic_vars or
        var_name in skip_vars
    )
