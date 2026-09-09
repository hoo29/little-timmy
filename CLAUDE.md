# CLAUDE.md

Guidance for working on little-timmy, a CLI that finds unused and duplicated Ansible variables.

## Layout

- `little_timmy/__main__.py` - CLI entrypoint, arg parsing, output and exit codes. Holds `VERSION`.
- `little_timmy/config_loader.py` - `.little-timmy` config schema and defaults, `setup_run()` which builds the
  ansible `DataLoader`, vault secrets, jinja environment and the shared `Context`.
- `little_timmy/unused_var_finder.py` - walks group_vars, host_vars, vars, defaults, inventories, playbooks, tasks,
  handlers, templates and molecule files and records declared vs referenced variables.
- `little_timmy/duplicated_var_finder.py` - compares variable values across group precedence levels per host.
- `little_timmy/taml.py` - YAML walking and jinja AST parsing helpers used to find variable references.
- `little_timmy/utils.py` - file globbing, cached file loading, vault handling helpers and skip logic.
- `github_action/` - Dockerfile and entrypoint for the GitHub action. `action.yml` is the action definition.
- `tests/` - pytest suite driven by fixture repos in `tests/repos/`.

## Conventions

- Support ansible >= 3 with both ansible < 12 (ansible-core < 2.19) and ansible >= 12 (ansible-core >= 2.19).
  Where internals differ, guard imports with `try/except ImportError` as done in `config_loader.py` and `utils.py`.
- Python >= 3.9. Avoid syntax or typing features newer than that.
- Results go to stdout. Logging and warnings go to stderr via the `little-timmy` logger so stdout can be piped.
  `-j` disables the logger entirely and prints only JSON to stdout.
- Never fail the whole run because of a single file or value that cannot be processed if it can be warned about
  and skipped instead.
- Do not print decrypted vault values. Compare vaulted values by cipher text.

## Testing

```sh
pip install -e ".[tests]"
pytest -vv
```

Each directory in `tests/repos/<name>/` has a `repo/` with an ansible layout, an `unused_vars` file listing the
expected unused variable names one per line, and optionally a `duplicated_vars` file with lines of
`HOST##VAR##VALUE##["relative/location", ...]`. Adding a new directory automatically adds a test case.

`tests/conftest.py` sets `ANSIBLE_VAULT_PASSWORD_FILE` to `tests/ansible_vault_password` if it is not already set.
Vault fixtures that should decrypt must be encrypted with that password. CI also runs the E2E commands in
`.github/workflows/test_module.yml`, keep them working.

## Releasing and version bumps

Versions follow semver. To bump a version update all of:

1. `version` in `pyproject.toml`
2. `VERSION` in `little_timmy/__main__.py`
3. The `little-timmy==X.Y.Z` pin in `github_action/Dockerfile`
4. A new `## [X.Y.Z] - YYYY/MM/DD` entry at the top of `CHANGELOG.md`

Publishing to PyPI and GHCR is done manually via the `workflow_dispatch` workflows in `.github/workflows/`.
Git tags are only used for the GitHub action (`v3-action`) and do not track the python module version.
