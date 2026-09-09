import logging
import os

from ansible.errors import AnsibleParserError
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import AnsibleVaultError, AnsibleVaultFormatError, AnsibleVaultPasswordError
from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode
try:
    # ansible >= 12 (ansible-core >= 2.19) loads inline vaulted values as EncryptedString
    from ansible.parsing.vault import EncryptedString
    VAULT_VALUE_TYPES = (AnsibleVaultEncryptedUnicode, EncryptedString)
except ImportError:
    # ansible < 12 (ansible-core < 2.19)
    VAULT_VALUE_TYPES = (AnsibleVaultEncryptedUnicode,)
from glob import iglob

LOGGER = logging.getLogger("little-timmy")

# AnsibleVaultFormatError is not a subclass of AnsibleVaultError in all ansible versions
VAULT_ERRORS = (AnsibleVaultError, AnsibleVaultFormatError,
                AnsibleVaultPasswordError)

# The DataLoader cache is not working so use our own basic one
loader_cache = {}

# Files a vault warning has already been emitted for, to avoid repeating it for every value
vault_warned_files: set[str] = set()


def warn_vault_error(path: str, err: Exception, message: str) -> None:
    """
    Warn, once per file, that vaulted content could not be decrypted.
    Warnings go to the stderr logger so stdout output can still be piped.
    """
    if path in vault_warned_files:
        return
    vault_warned_files.add(path)
    LOGGER.warning(
        f"WARNING: {message} Provide the matching vault password, e.g. via "
        f"ANSIBLE_VAULT_PASSWORD_FILE or ANSIBLE_VAULT_IDENTITY_LIST, to include it. Ansible error: {err}")


def is_vault_value(value: any) -> bool:
    return isinstance(value, VAULT_VALUE_TYPES)


def decrypt_vault_value(value: any, source: str):
    """
    Return the decrypted value of an inline vaulted value.
    Returns None, after warning, if it cannot be decrypted e.g. missing password or vault id.
    """
    try:
        return str(value)
    except VAULT_ERRORS as err:
        warn_vault_error(
            source, err, f"Unable to decrypt a vaulted value in {source} so its content will not be checked for variable usage.")
        return None


def replace_vault_values_with_ciphertext(value: any):
    """
    Recursively replace inline vaulted values with their cipher text so they can be
    compared without decrypting them or exposing them in output.
    """
    if is_vault_value(value):
        try:
            # wrap in try catch as we are accessing a hidden field
            return value._ciphertext
        except Exception:
            return None
    if isinstance(value, dict):
        return {k: replace_vault_values_with_ciphertext(v) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_vault_values_with_ciphertext(v) for v in value]
    return value


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
    if path not in loader_cache:
        try:
            loader_cache[path] = loader.load_from_file(path) or {}
        except VAULT_ERRORS as err:
            # Whole file is vaulted and cannot be decrypted. Skip it rather than fail
            warn_vault_error(
                path, err, f"Unable to decrypt vaulted file {path} so it will be skipped.")
            loader_cache[path] = {}
        except AnsibleParserError as err:
            raise ValueError(f"Ansible parse error for file {path}") from err
    return loader_cache[path]


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
