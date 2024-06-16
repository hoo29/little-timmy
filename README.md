# little-timmy

Little Timmy will try their best to find those unused Ansible variables.

```sh
cd repo/ansible/plays
ansible-galaxy collection install -f -r requirements.yml -p .
ansible-galaxy role install -f -r requirements.yml -p galaxy_roles

pip3 install little-timmy
little-timmy
```
