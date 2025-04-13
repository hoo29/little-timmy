# little-timmy

Little Timmy will try their best to find those unused and duplicated Ansible variables.

```sh
cd repo/ansible/plays
ansible-galaxy collection install -f -r requirements.yml -p .
ansible-galaxy role install -f -r requirements.yml -p galaxy_roles

pip3 install little-timmy

little-timmy
# or 
python3 -m little_timmy
```

It will find

- Most unused variables in:
  - `group_vars`
  - `host_vars`
  - `vars`
  - `defaults`
  - `set_facts` - when not defined as key value pairs on a single line
  - `register`
  - Inventory files
- Duplicated variables that have the same value at different group levels.
- Duplicated variables that have been defined multiple times at the same group level.

It is unlikely to find unused variables or may generate false positives for:

- Complex, dynamically referenced or created variables
- Variables referenced by YAML anchors
- Variables consumed in any custom python filters or similar
- Non standard(ish) directory layouts

False positives can be ignored with a config file detailed in the [Config](#config) section.

Please raise issues with any problems, ideas, or contributions with improvements!

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
        uses: hoo29/little-timmy@v2-action
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

The latest version can be found in [CHANGELOG.md](./CHANGELOG.md).

The tags on this repo are used for the Github action and do not relate the published
python module.

## Config

Additional, optional configuration can be specified in a YAML configuration file named `.little-timmy`.
The file can be located at any level between the current working directory and `/`.

The schema for the file is:

```python
{
    "type": "object",
    "properties": {
        "galaxy_dirs": {
            "description": "Directories where ansible-galaxy collections and roles have been installed. Must be within the directory being scanned.",
            "default": ["ansible_collections", "galaxy_roles"],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "skip_vars": {
            "description": "Variables to skip checking.",
            "default": [],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "skip_vars_duplicates_substrings": {
            "description": "Variables containing these substring will not be checked for duplication. This is in addition to skip_vars.",
            "default": ["pass", "vault"],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "skip_dirs": {
            "description": "Directories to skip loading files from.",
            "default": ["molecule", "venv", "tests"],
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "extra_jinja_context_keys": {
            "description": """
            Locations where there is already a jinja context for evaluation e.g. `when` and `assert.that`.
            Does not require module FQCN. Values are added to .config_loader.DEFAULT_JINJA_CONTEXT_KEYS.
            """,
            "default": [],
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "additionalProperties": False
}
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
  -du, --duplicated-vars, --no-duplicated-vars
                        Find duplicated variables.
  -e, --exit-success, --no-exit-success
                        Exit 0 when unused vars are found.
  -g, --github-action, --no-github-action
                        Output results for github actions.
  -j, --json-output, --no-json-output
                        Output results as json to stdout. Disables the stderr logger.
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        set the logging level (default: INFO).
  -u, --unused-vars, --no-unused-vars
                        Find unused variables.
  -v, --version, --no-version
                        Output the version.
```
