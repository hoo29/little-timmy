import os

from ansible.parsing.vault import AnsibleVaultError, AnsibleVaultFormatError, AnsibleVaultPasswordError
from jinja2 import exceptions, meta, nodes, Template

from .config_loader import Context
from .utils import skip_var


def walk_template_ast_arg(cur_node: any, context: Context):
    more_vars: set[str] = set()
    for arg in cur_node.args:
        if isinstance(arg, nodes.Const):
            more_vars = more_vars.union(meta.find_undeclared_variables(
                context.jinja_env.parse(arg.value)))
    return more_vars


def walk_template_ast_items(cur_node: any, context: Context):
    more_vars: set[str] = set()
    for item in cur_node.items:
        if isinstance(item, nodes.CondExpr):
            for expr in [x for x in [item.expr1, item.expr2] if isinstance(x, nodes.Const)]:
                more_vars = more_vars.union(meta.find_undeclared_variables(
                    context.jinja_env.parse(expr.value)))
    return more_vars


def walk_template_ast(value: Template, context: Context):
    """
    When meta.find_undeclared_variables says "all variables are returned"
    it really means "top level" variables. Args to the various plugins
    are not always evaluated and items can be missed. This function manually 
    checks other areas of interest in the AST.
    """
    more_vars: set[str] = set()
    if "body" not in value.fields or not isinstance(value.body, list):
        return more_vars

    for body in value.body:
        if "nodes" not in body.fields or not isinstance(body.nodes, list):
            break
        node_list = body.nodes
        while node_list:
            cur_node = node_list.pop()
            if (all(field in cur_node.fields for field in ["arg", "ctx"])
                and isinstance(cur_node.arg, nodes.Const)
                    and cur_node.ctx == "load" and isinstance(cur_node.arg.value, str)):
                value = cur_node.arg.value
                if "{{" not in value:
                    value = "{{ " + value + " }}"
                more_vars = more_vars.union(meta.find_undeclared_variables(
                    context.jinja_env.parse(value)))

            if "args" in cur_node.fields and isinstance(cur_node.args, list):
                more_vars = walk_template_ast_arg(cur_node, context)

            if "items" in cur_node.fields and isinstance(cur_node.items, list):
                more_vars = walk_template_ast_items(cur_node, context)

            if "node" in cur_node.fields:
                node_list.append(cur_node.node)

    return more_vars


def parse_jinja(value: any, source: str, context: Context, jinja_context: bool = False):
    if jinja_context:
        value = str(value)
        if "{{" not in value:
            # seems legit
            value = "{{ " + value + " }}"

    try:
        parsed = context.jinja_env.parse(value)
    except (AnsibleVaultError or AnsibleVaultFormatError or AnsibleVaultPasswordError) as err:
        raise ValueError(f"Ansible vault error for file {source}") from err
    except exceptions.TemplateError as err:
        err_msg = f"Jinja template error for file {source} value {value}"
        raise ValueError(err_msg) from err
    referenced_vars = meta.find_undeclared_variables(parsed)
    referenced_vars = referenced_vars.union(
        walk_template_ast(parsed, context))
    for referenced_var in referenced_vars:
        context.all_referenced_vars[referenced_var].add(source)


def add_declared_var(var_name: str, source: str, context: Context):
    relative_path = os.path.dirname(os.path.relpath(source, context.root_dir))
    external = any(
        excluded_dir in relative_path for excluded_dir in context.config.dirs_not_to_delcare_vars_from)
    if not external:
        context.all_declared_vars[var_name].add(source)


def walk_variable(var_value: any, source: str, context: Context):
    """
    Nested > or | have a habit of making jinja_env.parse explode
    so walk variables to escape the strings.
    I'm sure there is a function in jinja to deal with this for me...
    """
    if isinstance(var_value, str):
        var_value = var_value.replace(os.linesep, " ")
    if isinstance(var_value, list):
        for item in var_value:
            walk_variable(item, source, context)
    elif isinstance(var_value, dict):
        for _, value in var_value.items():
            walk_variable(value, source, context)
    else:
        parse_jinja(var_value, source, context)


def parse_yaml_variable(var_name: str, var_value: any, source: str, context: Context):
    if skip_var(var_name, context.config.magic_vars, context.config.skip_vars):
        return
    add_declared_var(var_name, source, context)
    walk_variable(var_value, source, context)


def is_in_jinja_context(history: str, context: Context) -> bool:
    return history.endswith(context.config.jinja_context_keys)


def parse_yaml_dict(contents: dict, source: str, context: Context, history: str = ""):
    for k, v in contents.items():
        if k == "register":
            add_declared_var(v, source, context)
        elif k == "index_var" and history.endswith("loop_control"):
            add_declared_var(v, source, context)
        elif (k == "vars" or k.endswith("set_fact")) and isinstance(v, dict):
            for var_name, var_value in v.items():
                parse_yaml_variable(var_name, var_value, source, context)
        elif isinstance(v, int) or isinstance(v, str) or isinstance(v, bool):
            jinja = is_in_jinja_context(f"{history}.{k}", context)
            parse_jinja(v, source, context, jinja)
        elif isinstance(v, list):
            parse_yaml_list(v, source, context, f"{history}.{k}")
        elif isinstance(v, dict):
            parse_yaml_dict(v, source, context, f"{history}.{k}")
        else:
            continue


def parse_yaml_list(contents: list[dict], source: str, context: Context, history: str = ""):
    for item in contents:
        if isinstance(item, dict):
            parse_yaml_dict(item, source, context, history)
        if isinstance(item, str):
            jinja = is_in_jinja_context(history, context)
            parse_jinja(item, source, context, jinja)
