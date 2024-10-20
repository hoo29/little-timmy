#!/bin/sh -le

echo "Changing directory to $INPUT_DIRECTORY"
cd "$INPUT_DIRECTORY"

if [ -n "$INPUT_GALAXY_ROLE_REQUIREMENTS_FILE" ]; then
    echo "Installing ansible galaxy roles from $INPUT_GALAXY_ROLE_REQUIREMENTS_FILE"
    ansible-galaxy role install -f -r "$INPUT_GALAXY_ROLE_REQUIREMENTS_FILE" -p galaxy_roles
fi

if [ -n "$INPUT_GALAXY_COLLECTION_REQUIREMENTS_FILE" ]; then
    echo "Installing ansible galaxy collections from $INPUT_GALAXY_COLLECTION_REQUIREMENTS_FILE"
    ansible-galaxy collection install -f -r "$INPUT_GALAXY_COLLECTION_REQUIREMENTS_FILE" -p .
fi

printenv INPUT_ANSIBLE_VAULT_PASSWORD >ansible_vault_password
export ANSIBLE_VAULT_PASSWORD_FILE="ansible_vault_password"

echo "Running little-timmy"
# shellcheck disable=SC2086
little-timmy -g $INPUT_ADDITIONAL_CLI_ARGS

echo "Done"
