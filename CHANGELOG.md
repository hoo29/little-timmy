# Changelog

Change log for the little-timmy python module.

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
