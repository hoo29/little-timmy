# little-timmy

Little Timmy will try their best to find those unused Ansible variables.

```sh
cd repo/ansible/plays
ansible-galaxy collection install -f -r requirements.yml -p .
ansible-galaxy role install -f -r requirements.yml -p galaxy_roles

pip3 install little-timmy

little-timmy
# or 
python3 -m little_timmy
```

Little Timmy can find the "80%" of unused variables but due to the numerous ways variables can be declared
and consumed in Ansible, some will be missed.

It should find unused variables in:

- `group_vars`
- `host_vars`
- `vars`
- `defaults`
- Inventory files

The above files are parsed to find variable declarations followed by a rudimentary search for their usage in
playbooks, templates, tasks, and handler files.

It will not find unused variables for:

- `set_facts`
- `register`
- Dynamically created or referenced variables
- Variables consumed in any custom python filters or similar

## Github Action

Workflow

```yaml
name: little-timmy
on:
  push:
jobs:
  little-timmy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run action
        uses: hoo29/little-timmy@v1-action
```

Variables

```yaml
inputs:
  directory:
    description: The root directory for your ansible
    required: false
    default: "."
  additional_cli_args:
    description: Additional CLI arguments to pass to little-timmy
    required: false
    default: ""
  galaxy_role_requirements_file:
    description: Location, relative to `directory`, of the ansible galaxy roles requirements file.
    required: false
  galaxy_collection_requirements_file:
    description: Location, relative to `directory`, of the ansible galaxy collections requirements file.
    required: false
  ansible_vault_password:
    description: |
      Optional ansible-vault password. The content will be a written to a 
      file and ANSIBLE_VAULT_PASSWORD_FILE set to its location. Only used
      by ansible if a vaulted value is found.
    required: false
    default: replace-me-if-vault-is-used
```

## Version and Tags

The latest version can be found in [pyproject.toml](./pyproject.toml) and the
changelog is [CHANGELOG.md](./CHANGELOG.md).

The tags on this repo are used for the Github action and do not relate the published
python module.

## Config

Additional, optional configuration can be specified in a YAML configuration file named `.little-timmy`.
The file can be located at any level between the current working directory and `/`.

```yaml
skip_vars:
  - vars
  - to
  - ignore
skip_dirs:
  - venv
  - tests
  - molecule
```

## Help

```text
little-timmy -h

usage: little-timmy [OPTIONS] [directory]

Process a directory path

positional arguments:
  directory             The directory to process

options:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Config file to use. By default it will search all dirs to `/` for .little-timmy
  -d, --dave-mode, --no-dave-mode
                        Make logging work on dave's macbook.
  -e, --exit-success, --no-exit-success
                        Exit 0 when unused vars are found.
  -g, --github-action, --no-github-action
                        Output results for github actions.
  -j, --json-output, --no-json-output
                        Output results as json to stdout. Disables the stderr logger.
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        set the logging level (default: INFO).
  -v, --version, --no-version
                        Output the version.
```
