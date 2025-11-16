# Changelog

Change log for the little-timmy python module.

## [3.5.0] - 2025/11/16

- Support custom filters in collections @copilot/@hoo29

## [3.4.0] - 2025/11/02

- Add compatibility with ansible >= 12 by adapting to jinja templating internals refactor @copilot

## [3.3.3] - 2025/10/13

- Fix for not finding loop_var @einunderstzig

## [3.3.2] - 2025/10/11

- Update dependencies to ansible >= 3.0.0, < 12.0.0 because of a major refactor of jinja in
<https://github.com/ansible/ansible/pull/84621>

## [3.3.1] - 2025/09/01

- Fix for not finding unused var when using string of var name as index

## [3.3.0] - 2025/06/27

- Make template and playbook globs configurable

## [3.2.0] - 2025/06/24

- Don't parse !unsafe variables @einunderstzig

## [3.1.3] - 2025/06/24

- Don't look at the value of skipped variables.

## [3.1.2] - 2025/06/23

- Fix nested dict lookups with ":" chars in string

## [3.1.1] - 2025/06/14

- Consider skip_vars for register, index_var and loop_control @parsa97

## [3.1.0] - 2025/04/15

- Deduplicate duplicated variable outputs for multiple hosts in the same groups.

## [3.0.0] - 2025/04/13

- Add support for finding duplicated variables that have the same value at different group levels and finding variables that have been defined
multiple times at the same group level.

    For example if a host was a member of the groups (in heirarchal order): `["all", "g0", "g1", "g2", "g3"]`

    ```text
    .
    ├── group_vars
    │   ├── all
    │   │   ├── file0.yml dns: 1.1.1.1
    │   │   └── file1.yml dns: 2.2.2.2 # flagged, conflicting definition with file0.yml
    │   ├── g0.yml dns: 8.8.8.8
    │   ├── g1.yml dns: 8.8.8.8 # flagged, duplicate of parent group g0
    │   ├── g2.yml dns: 1.1.1.1
    │   └── g3.yml dns: 1.1.1.1 # flagged, duplicate of parent group g2
    └── inventories
        └── site_a.yml
    ```

    This behaviour is enabled by default and can be disabled by providing the arg `--no-duplicated-vars`. Currently, it requires the inventory files to
    be in a subdirectory called `inventory` or `inventories`.

    Variables which contain substrings defined in the new config item `skip_vars_duplicates_substrings` will be skipped.
    This defaults to `["pass", "vault"]`.

- Add CLI flag `--no-unused-vars` to only run the duplication check.
- Changed the structure of the json output mode. There is a new `type` property which will either be `UNUSED` or `DUPLICATED` depending on the
violation found. For `DUPLICATED` variables, the name format is `INVENTORY_HOST##VARIABLE_NAME##VARIABLE_VALUE` and in addition to the standard
`locations` property, there is a `original` property which specifies where the variable is defined at the top most precedence level.

## [2.2.0] - 2025/01/25

- Skip scanning dynamic inventory files because they generate false positives.

## [2.1.1] - 2024/11/03

- Fix sending non json result output to stdout instead of stderr @leventyalcin

## [2.1.0] - 2024/10/31

- Add support for CondExpr jinja parsing.
- Add limited support for finding strings used as index lookups. e.g. finding primary in `when: hostvars[item]['primary']`

## [2.0.2] - 2024/10/31

- Fix parsing roles which are called "defaults".
- Fix finding config files when the path ended with a `/`.

## [2.0.1] - 2024/10/20

- Update the -v string!

## [2.0.0] - 2024/10/20

Now parses all files instead of performing basic regex searches.

- Add support for variables declared in vars, set_facts, and register.
- Reduce runtime by about 50%.

## [1.2.0] - 2024/10/13

- Add support for using custom filter plugins.
- Remove basic filter fallback added in 1.1.2 to highlight future issues.

## [1.1.2] - 2024/10/13

- Fix `jinja2.exceptions.TemplateSyntaxError` when loading templates with custom filters by failing back to basic searching.
- Add `-v` version output.

## [1.1.1] - 2024/10/05

- Fix erroneous new line in `-g` output.

## [1.1.0] - 2024/10/05

- Add `-g` for github action workflow output

## [1.0.0] - 2024/08/24

- v1 release
