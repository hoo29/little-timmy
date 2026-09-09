import os

# Must be set before ansible constants are imported (via little_timmy.config_loader) so that
# tests behave the same locally as in CI where ANSIBLE_VAULT_PASSWORD_FILE is set explicitly.
os.environ.setdefault(
    "ANSIBLE_VAULT_PASSWORD_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ansible_vault_password"))
