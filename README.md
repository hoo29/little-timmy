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

## Config

Additional, optional configuration can be specified in a YAML configuration file named `.little-timmy`.
The file can be located at any level between the current working directory and `/`.

```yaml
skip_vars:
  - vars
  - to
  - ignore
```

## Help

```text
little-timmy -h
usage: little-timmy [-h] [-l LOG_LEVEL] [-c CONFIG_FILE] [-d | --dave-mode | --no-dave-mode] [directory]

Process a directory path

positional arguments:
  directory             The directory to process

options:
  -h, --help            show this help message and exit
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        set the logging level (default: INFO)
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Config file to use. By default it will search all dirs to `/` for .little-timmy
  -d, --dave-mode, --no-dave-mode
                        Make logging work on dave's macbook
```
