from __future__ import absolute_import

import importlib as _importlib
import os as _os
import sys as _sys
import stat as _stat

import click as _click
import six as _six
from flyteidl.core import literals_pb2 as _literals_pb2

from flytekit import __version__
from flytekit.clients import friendly as _friendly_client
from flytekit.clis.helpers import construct_literal_map_from_variable_map as _construct_literal_map_from_variable_map, \
    construct_literal_map_from_parameter_map as _construct_literal_map_from_parameter_map, \
    parse_args_into_dict as _parse_args_into_dict, str2bool as _str2bool
from flytekit.common import utils as _utils, launch_plan as _launch_plan_common
from flytekit.common.core import identifier as _identifier
from flytekit.common.types import helpers as _type_helpers
from flytekit.common.utils import load_proto_from_file as _load_proto_from_file
from flytekit.configuration import platform as _platform_config
from flytekit.interfaces.data import data_proxy as _data_proxy
from flytekit.models import common as _common_models, filters as _filters, launch_plan as _launch_plan, literals as \
    _literals
from flytekit.models.admin import common as _admin_common
from flytekit.models.core import execution as _core_execution_models
from flytekit.models.execution import ExecutionSpec as _ExecutionSpec, ExecutionMetadata as _ExecutionMetadata
from flytekit.models.project import Project as _Project
from flytekit.models.schedule import Schedule as _Schedule

_tt = _six.text_type


def _welcome_message():
    _click.secho("Welcome to Flyte CLI! Version: {}".format(_tt(__version__)), bold=True)


def _get_io_string(literal_map, verbose=False):
    """
    :param flytekit.models.literals.LiteralMap literal_map:
    :param bool verbose:
    :rtype: Text
    """
    value_dict = _type_helpers.unpack_literal_map_to_sdk_object(literal_map)
    if value_dict:
        return "\n" + "\n".join(
            "{:30}: {}".format(
                k,
                _prefix_lines("{:30}  ".format(""), v.verbose_string() if verbose else v.short_string())
            ) for k, v in _six.iteritems(value_dict)
        )
    else:
        return "(None)"


def _fetch_and_stringify_literal_map(path, verbose=False):
    """
    :param Text path:
    :param bool verbose:
    :rtype: Text
    """
    with _utils.AutoDeletingTempDir("flytecli") as tmp:
        try:
            fname = tmp.get_named_tempfile("literalmap.pb")
            _data_proxy.Data.get_data(path, fname)
            literal_map = _literals.LiteralMap.from_flyte_idl(
                _utils.load_proto_from_file(_literals_pb2.LiteralMap, fname)
            )
            return _get_io_string(literal_map, verbose=verbose)
        except:
            return "Failed to pull data from {}. Do you have permissions?".format(path)


def _prefix_lines(prefix, txt):
    """
    :param Text prefix:
    :param Text txt:
    :rtype: Text
    """
    return "\n{}".format(prefix).join(txt.splitlines())


def _secho_workflow_status(status, nl=True):
    red_phases = {
        _core_execution_models.WorkflowExecutionPhase.FAILED,
        _core_execution_models.WorkflowExecutionPhase.ABORTED,
        _core_execution_models.WorkflowExecutionPhase.FAILING,
        _core_execution_models.WorkflowExecutionPhase.TIMED_OUT
    }
    yellow_phases = {
        _core_execution_models.WorkflowExecutionPhase.QUEUED,
        _core_execution_models.WorkflowExecutionPhase.UNDEFINED
    }
    green_phases = {
        _core_execution_models.WorkflowExecutionPhase.SUCCEEDED,
        _core_execution_models.WorkflowExecutionPhase.SUCCEEDING
    }
    if status in red_phases:
        fg = 'red'
    elif status in yellow_phases:
        fg = 'yellow'
    elif status in green_phases:
        fg = 'green'
    else:
        fg = 'blue'

    _click.secho(
        "{:10} ".format(_tt(_core_execution_models.WorkflowExecutionPhase.enum_to_string(status))),
        bold=True,
        fg=fg,
        nl=nl
    )


def _secho_node_execution_status(status, nl=True):
    red_phases = {
        _core_execution_models.NodeExecutionPhase.FAILING,
        _core_execution_models.NodeExecutionPhase.FAILED,
        _core_execution_models.NodeExecutionPhase.ABORTED,
        _core_execution_models.NodeExecutionPhase.TIMED_OUT
    }
    yellow_phases = {
        _core_execution_models.NodeExecutionPhase.QUEUED,
        _core_execution_models.NodeExecutionPhase.UNDEFINED
    }
    green_phases = {
        _core_execution_models.NodeExecutionPhase.SUCCEEDED
    }
    if status in red_phases:
        fg = 'red'
    elif status in yellow_phases:
        fg = 'yellow'
    elif status in green_phases:
        fg = 'green'
    else:
        fg = 'blue'

    _click.secho(
        "{:10} ".format(_tt(_core_execution_models.NodeExecutionPhase.enum_to_string(status))),
        bold=True,
        fg=fg,
        nl=nl
    )


def _secho_task_execution_status(status, nl=True):
    red_phases = {
        _core_execution_models.TaskExecutionPhase.ABORTED,
        _core_execution_models.TaskExecutionPhase.FAILED,
    }
    yellow_phases = {
        _core_execution_models.TaskExecutionPhase.QUEUED,
        _core_execution_models.TaskExecutionPhase.UNDEFINED,
        _core_execution_models.TaskExecutionPhase.RUNNING
    }
    green_phases = {
        _core_execution_models.TaskExecutionPhase.SUCCEEDED
    }
    if status in red_phases:
        fg = 'red'
    elif status in yellow_phases:
        fg = 'yellow'
    elif status in green_phases:
        fg = 'green'
    else:
        fg = 'blue'

    _click.secho(
        "{:10} ".format(_tt(_core_execution_models.TaskExecutionPhase.enum_to_string(status))),
        bold=True,
        fg=fg,
        nl=nl
    )


def _secho_one_execution(ex, urns_only):
    if not urns_only:
        _click.echo(
            "{:100} {:40} ".format(
                _tt(_identifier.WorkflowExecutionIdentifier.promote_from_model(ex.id)),
                _tt(ex.id.name)
            ),
            nl=False
        )
        _secho_workflow_status(ex.closure.phase)
    else:
        _click.echo(
            "{:100}".format(
                _tt(_identifier.WorkflowExecutionIdentifier.promote_from_model(ex.id))
            ),
            nl=True
        )


def _terminate_one_execution(client, urn, cause, shouldPrint=True):
    if shouldPrint:
        _click.echo("{:100} {:40}".format(_tt(urn), _tt(cause)))
    client.terminate_execution(
        _identifier.WorkflowExecutionIdentifier.from_python_std(urn),
        cause
    )


def _update_one_launch_plan(urn, host, insecure, state):
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    if state == "active":
        state = _launch_plan.LaunchPlanState.ACTIVE
    else:
        state = _launch_plan.LaunchPlanState.INACTIVE
    client.update_launch_plan(_identifier.Identifier.from_python_std(urn), state)
    _click.echo("Successfully updated {}".format(_tt(urn)))


def _render_schedule_expr(lp):
    sched_expr = "NONE"
    if lp.spec.entity_metadata.schedule.cron_expression:
        sched_expr = "cron({cron_expr})".format(
            cron_expr=_tt(lp.spec.entity_metadata.schedule.cron_expression)
        )
    elif lp.spec.entity_metadata.schedule.rate:
        sched_expr = "rate({unit}={value})".format(
            unit=_tt(_Schedule.FixedRateUnit.enum_to_string(
                lp.spec.entity_metadata.schedule.rate.unit
            )),
            value=_tt(lp.spec.entity_metadata.schedule.rate.value)
        )
    return "{:30}".format(sched_expr)


_HOST_URL_ENV = _os.environ.get(_platform_config.URL.env_var, None)
_INSECURE_ENV = _os.environ.get(_platform_config.INSECURE.env_var, None)
_PROJECT_FLAGS = ["-p", "--project"]
_DOMAIN_FLAGS = ["-d", "--domain"]
_NAME_FLAGS = ["-n", "--name"]
_HOST_FLAGS = ["-h", "--host"]
_PRINCIPAL_FLAGS = ["-r", "--principal"]
_INSECURE_FLAGS = ["-i", "--insecure"]

_project_option = _click.option(
    *_PROJECT_FLAGS,
    required=True,
    help="The project namespace to query."
)
_optional_project_option = _click.option(
    *_PROJECT_FLAGS,
    required=False,
    default=None,
    help="[Optional] The project namespace to query."
)
_domain_option = _click.option(
    *_DOMAIN_FLAGS,
    required=True,
    help="The domain namespace to query."
)
_optional_domain_option = _click.option(
    *_DOMAIN_FLAGS,
    required=False,
    default=None,
    help="[Optional] The domain namespace to query."
)
_name_option = _click.option(
    *_NAME_FLAGS,
    required=True,
    help="The name to query."
)
_optional_name_option = _click.option(
    *_NAME_FLAGS,
    required=False,
    type=str,
    default=None,
    help="[Optional] The name to query."
)
_principal_option = _click.option(
    *_PRINCIPAL_FLAGS,
    required=True,
    help="Your team name, or your name"
)
_optional_principal_option = _click.option(
    *_PRINCIPAL_FLAGS,
    required=False,
    type=str,
    default=None,
    help="[Optional] Your team name, or your name"
)
_insecure_option = _click.option(
    *_INSECURE_FLAGS,
    is_flag=True,
    required=True,
    help="Do not use SSL"
)
_insecure_optional_option = _click.option(
    *_INSECURE_FLAGS,
    is_flag=True,
    required=False,
    default=False if _INSECURE_ENV is None else _str2bool(_INSECURE_ENV),
    help="Do not use SSL communication"
)
_urn_option = _click.option(
    "-u", "--urn",
    required=True,
    help="The unique identifier for an entity."
)

_optional_urn_option = _click.option(
    "-u", "--urn",
    required=False,
    help="The unique identifier for an entity."
)

_host_option = _click.option(
    *_HOST_FLAGS,
    required=not bool(_HOST_URL_ENV),
    default=_HOST_URL_ENV,
    help="The URL for the Flyte Admin Service. If you intend for this to be consistent, set the FLYTE_PLATFORM_URL "
         "environment variable to the desired URL and this will not need to be set."
)
_token_option = _click.option(
    "-t", "--token",
    required=False,
    default="",
    type=str,
    help="Pagination token from which to start listing in the list of results."
)
_limit_option = _click.option(
    "-l", "--limit",
    required=False,
    default=100,
    type=int,
    help="Maximum number of results to return for this call."
)
_show_all_option = _click.option(
    "-a", "--show-all",
    is_flag=True,
    default=False,
    help="Set this flag to page through and list all results."
)
# TODO: Provide documentation on filter format
_filter_option = _click.option(
    "-f", "--filter",
    multiple=True,
    help="Filter to be applied.  Multiple filters can be applied and they will be ANDed together."
)
_state_choice = _click.option(
    "--state",
    type=_click.Choice(["active", "inactive"]),
    required=True,
    help="Whether or not to set schedule as active."
)
_sort_by_option = _click.option(
    "--sort-by",
    required=False,
    help="Provide an entity type and field to be sorted.  i.e. asc(workflow.name) or desc(workflow.name)"
)
_show_io_option = _click.option(
    "--show-io",
    is_flag=True,
    default=False,
    help="Set this flag to view inputs and outputs.  Pair with the --verbose flag to get the full textual description"
         " inputs and outputs."
)
_verbose_option = _click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Set this flag to view the full textual description of all fields."
)

_filename_option = _click.option(
    '-f', '--filename',
    required=True,
    help="File path of pb file"
)
_idl_class_option = _click.option(
    '-p', '--proto_class',
    required=True,
    help="Dot (.) separated path to Python IDL class. (e.g. flyteidl.core.workflow_closure_pb2.WorkflowClosure)"
)
_cause_option = _click.option(
    '-c', '--cause',
    required=True,
    help="The message signaling the cause of the termination of the execution(s)"
)
_optional_urns_only_option = _click.option(
    '--urns-only',
    is_flag=True,
    default=False,
    required=False,
    help="[Optional] Set the flag if you want to list the urns only"
)
_project_identifier_option = _click.option(
    '-i', '--identifier',
    required=True,
    type=str,
    help="Unique identifier for the project."
)
_project_name_option = _click.option(
    '-n', '--name',
    required=True,
    type=str,
    help="The human-readable name for the project."
)


class _FlyteSubCommand(_click.Command):
    _PASSABLE_ARGS = {
        'project': _PROJECT_FLAGS[0],
        'domain': _DOMAIN_FLAGS[0],
        'name': _NAME_FLAGS[0],
        'host': _HOST_FLAGS[0]
    }

    _PASSABLE_FLAGS = {
        'insecure': _INSECURE_FLAGS[0],
    }

    def make_context(self, cmd_name, args, parent=None):
        prefix_args = []
        for param in self.params:
            if param.name in type(self)._PASSABLE_ARGS and \
                    param.name in parent.params and \
                    parent.params[param.name] is not None:
                prefix_args.extend([type(self)._PASSABLE_ARGS[param.name], _six.text_type(parent.params[param.name])])

            # For flags, we don't append the value of the flag, otherwise click will fail to parse
            if param.name in type(self)._PASSABLE_FLAGS and \
                    param.name in parent.params and \
                    parent.params[param.name]:
                prefix_args.append(type(self)._PASSABLE_FLAGS[param.name])

        ctx = super(_FlyteSubCommand, self).make_context(cmd_name, prefix_args + args, parent=parent)
        return ctx


@_click.option(
    *_HOST_FLAGS,
    required=False,
    type=str,
    default=None,
    help="[Optional] The host to pass to the sub-command (if applicable).  If set again in the sub-command, "
         "the sub-command's parameter takes precedence."
)
@_click.option(
    *_PROJECT_FLAGS,
    required=False,
    type=str,
    default=None,
    help="[Optional] The project to pass to the sub-command (if applicable)  If set again in the sub-command, "
         "the sub-command's parameter takes precedence."
)
@_click.option(
    *_DOMAIN_FLAGS,
    required=False,
    type=str,
    default=None,
    help="[Optional] The domain to pass to the sub-command (if applicable)  If set again in the sub-command, "
         "the sub-command's parameter takes precedence."
)
@_click.option(
    *_NAME_FLAGS,
    required=False,
    type=str,
    default=None,
    help="[Optional] The name to pass to the sub-command (if applicable)  If set again in the sub-command, "
         "the sub-command's parameter takes precedence."
)
@_insecure_optional_option
@_click.group("flyte-cli")
@_click.pass_context
def _flyte_cli(ctx, project, domain, name, host, insecure):
    """
    Command line tool for interacting with all entities on the Flyte Platform.
    """
    pass


########################################################################################################################
#
#  Miscellaneous Commands
#
########################################################################################################################

@_flyte_cli.command('parse-proto', cls=_click.Command)
@_filename_option
@_idl_class_option
def parse_proto(filename, proto_class):
    _welcome_message()
    splitted = proto_class.split('.')
    idl_module = '.'.join(splitted[:-1])
    idl_obj = splitted[-1]
    mod = _importlib.import_module(idl_module)
    idl = getattr(mod, idl_obj)
    obj = _load_proto_from_file(idl, filename)

    _click.echo(obj)
    _click.echo("")


########################################################################################################################
#
#  Task Commands
#
########################################################################################################################

@_flyte_cli.command('list-task-names', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_sort_by_option
def list_task_names(project, domain, host, insecure, token, limit, show_all, sort_by):
    """
    List the name of the tasks that are in the registered workflow under
    a specific project and domain.
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Task Names Found in {}:{}\n".format(_tt(project), _tt(domain)))
    while True:
        task_ids, next_token = client.list_task_ids_paginated(
            project,
            domain,
            limit=limit,
            token=token,
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )
        for t in task_ids:
            _click.echo("\t{}".format(_tt(t.name)))

        if show_all is not True:
            if next_token:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token
    _click.echo("")


@_flyte_cli.command('list-task-versions', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_optional_name_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_filter_option
@_sort_by_option
def list_task_versions(project, domain, name, host, insecure, token, limit, show_all, filter, sort_by):
    """
    List all the versions of the tasks under a specific {Project, Domain} tuple.
    If the name of a certain task is supplied, this command will list all the
    versions of that particular task (identifiable by {Project, Domain, Name}).
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Task Versions Found for {}:{}:{}\n".format(_tt(project), _tt(domain), _tt(name or '*')))
    _click.echo("{:50} {:40}".format('Version', 'Urn'))
    while True:
        task_list, next_token = client.list_tasks_paginated(
            _common_models.NamedEntityIdentifier(
                project,
                domain,
                name
            ),
            limit=limit,
            token=token,
            filters=[_filters.Filter.from_python_std(f) for f in filter],
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )
        for t in task_list:
            _click.echo("{:50} {:40}".format(_tt(t.id.version), _tt(_identifier.Identifier.promote_from_model(t.id))))

        if show_all is not True:
            if next_token:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token
    _click.echo("")


@_flyte_cli.command('get-task', cls=_FlyteSubCommand)
@_urn_option
@_host_option
@_insecure_option
def get_task(urn, host, insecure):
    """
    Get the details of a certain version of a task identified by the URN of it.
    The URN of the versioned task is in the form of ``tsk:<project>:<domain>:<task_name>:<version>``.
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)
    t = client.get_task(_identifier.Identifier.from_python_std(urn))
    _click.echo(_tt(t))
    _click.echo("")


########################################################################################################################
#
#  Workflow Commands
#
########################################################################################################################

@_flyte_cli.command('list-workflow-names', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_sort_by_option
def list_workflow_names(project, domain, host, insecure, token, limit, show_all, sort_by):
    """
    List the names of the workflows under a scope specified by ``{project, domain}``.
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Workflow Names Found in {}:{}\n".format(_tt(project), _tt(domain)))
    while True:
        wf_ids, next_token = client.list_workflow_ids_paginated(
            project,
            domain,
            limit=limit,
            token=token,
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )
        for i in wf_ids:
            _click.echo("\t{}".format(_tt(i.name)))

        if show_all is not True:
            if next_token:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token
    _click.echo("")


@_flyte_cli.command('list-workflow-versions', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_optional_name_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_filter_option
@_sort_by_option
def list_workflow_versions(project, domain, name, host, insecure, token, limit, show_all, filter, sort_by):
    """
    List all the versions of the workflows under the scope specified by ``{project, domain}``.
    If the name of a a certain workflow is supplied, this command will list all the
    versions of that particular workflow (identifiable by ``{project, domain, name}``).
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Workflow Versions Found for {}:{}:{}\n".format(_tt(project), _tt(domain), _tt(name or '*')))
    _click.echo("{:50} {:40}".format('Version', 'Urn'))
    while True:
        wf_list, next_token = client.list_workflows_paginated(
            _common_models.NamedEntityIdentifier(
                project,
                domain,
                name
            ),
            limit=limit,
            token=token,
            filters=[_filters.Filter.from_python_std(f) for f in filter],
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )
        for w in wf_list:
            _click.echo("{:50} {:40}".format(_tt(w.id.version), _tt(_identifier.Identifier.promote_from_model(w.id))))

        if show_all is not True:
            if next_token:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token
    _click.echo("")


@_flyte_cli.command('get-workflow', cls=_FlyteSubCommand)
@_urn_option
@_host_option
@_insecure_option
def get_workflow(urn, host, insecure):
    """
    Get the details of a certain version of a workflow identified by the URN in the form of
    ``wf:<project>:<domain>:<workflow_name>:<version>``
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)
    _click.echo(client.get_workflow(_identifier.Identifier.from_python_std(urn)))
    # TODO: Print workflow pretty
    _click.echo("")


########################################################################################################################
#
#  Launch Plan Commands
#
########################################################################################################################

@_flyte_cli.command('list-launch-plan-names', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_sort_by_option
def list_launch_plan_names(project, domain, host, insecure, token, limit, show_all, sort_by):
    """
    List the names of the launch plans under the scope specified by {project, domain}.
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Launch Plan Names Found in {}:{}\n".format(_tt(project), _tt(domain)))
    while True:
        wf_ids, next_token = client.list_launch_plan_ids_paginated(
            project,
            domain,
            limit=limit,
            token=token,
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )
        for i in wf_ids:
            _click.echo("\t{}".format(_tt(i.name)))

        if show_all is not True:
            if next_token:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token
    _click.echo("")


@_flyte_cli.command('list-active-launch-plans', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_sort_by_option
@_optional_urns_only_option
def list_active_launch_plans(project, domain, host, insecure, token, limit, show_all, sort_by, urns_only):
    """
    List the information of all the active launch plans under the scope specified by {project, domain}.
    An active launch plan is a launch plan with an active schedule associated with it.
    """
    if not urns_only:
        _welcome_message()
        _click.echo("Active Launch Plan Found in {}:{}\n".format(_tt(project), _tt(domain)))
        _click.echo("{:50} {:80} {:15}".format('Version', 'Urn', "Schedule"))

    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    while True:
        active_lps, next_token = client.list_launch_plans_paginated(
            _common_models.NamedEntityIdentifier(
                project,
                domain
            ),
            limit=limit,
            token=token,
            filters=[
                _filters.Equal('state', '1'),
                _filters.ValueIn('schedule_type', ['CRON', 'RATE'])
            ],
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )

        for lp in active_lps:
            if urns_only:
                _click.echo("{:80}".format(
                    _tt(_identifier.Identifier.promote_from_model(lp.id))
                ))
            else:
                _click.echo(
                    "{:50} {:80} {:30}".format(
                        _tt(lp.id.version),
                        _tt(_identifier.Identifier.promote_from_model(lp.id)),
                        _render_schedule_expr(lp)
                    ),
                )

        if show_all is not True:
            if next_token and not urns_only:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token

    if not urns_only:
        _click.echo("")
    return


@_flyte_cli.command('list-launch-plan-versions', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_name_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_filter_option
@_sort_by_option
def list_launch_plan_versions(project, domain, name, host, insecure, token, limit, show_all, filter, sort_by):
    """
    List the versions of all the launch plans under the scope specified by {project, domain}.
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Launch Plan Versions Found for {}:{}:{}\n".format(_tt(project), _tt(domain), _tt(name)))

    _click.echo("{:50} {:80} {:30} {:15}".format('Version', 'Urn', "Schedule", "Schedule State"))

    while True:
        lp_list, next_token = client.list_launch_plans_paginated(
            _common_models.NamedEntityIdentifier(
                project,
                domain,
                name
            ),
            limit=limit,
            token=token,
            filters=[_filters.Filter.from_python_std(f) for f in filter],
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )
        for l in lp_list:
            _click.echo(
                "{:50} {:80} ".format(
                    _tt(l.id.version),
                    _tt(_identifier.Identifier.promote_from_model(l.id))
                ),
                nl=False
            )
            if l.spec.entity_metadata.schedule.cron_expression or l.spec.entity_metadata.schedule.rate:
                _click.echo(
                    "{:30} ".format(_render_schedule_expr(l)),
                    nl=False
                )
                _click.secho(
                    _launch_plan.LaunchPlanState.enum_to_string(l.closure.state),
                    fg="green" if l.closure.state == _launch_plan.LaunchPlanState.ACTIVE else None
                )
            else:
                _click.echo()

        if show_all is not True:
            if next_token:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token
    _click.echo("")


@_flyte_cli.command('get-launch-plan', cls=_FlyteSubCommand)
@_urn_option
@_host_option
@_insecure_option
def get_launch_plan(urn, host, insecure):
    """
    Get the details of a certain launch plan identified by the URN of that launch plan.
    The URN of a launch plan is in the form of ``lp:<project>:<domain>:<launch_plan_name>:<version>``
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)
    _click.echo(_tt(client.get_launch_plan(_identifier.Identifier.from_python_std(urn))))
    # TODO: Print launch plan pretty
    _click.echo("")


@_flyte_cli.command('update-launch-plan', cls=_FlyteSubCommand)
@_state_choice
@_host_option
@_insecure_option
@_optional_urn_option
def update_launch_plan(state, host, insecure, urn=None):
    _welcome_message()

    if urn is None:
        try:
            # Examine whether the input is from the named pipe
            if _stat.S_ISFIFO(_os.fstat(0).st_mode):
                for line in _sys.stdin.readlines():
                    _update_one_launch_plan(urn=line.rstrip(), host=host, insecure=insecure, state=state)
            else:
                # If the commandline parameter urn is not supplied, and neither
                # the input comes from a pipe, it means the user is not using
                # this command approperiately
                raise _click.UsageError('Missing option "-u" / "--urn" or missing pipe inputs')
        except KeyboardInterrupt:
            _sys.stdout.flush()
    else:
        _update_one_launch_plan(urn=urn, host=host, insecure=insecure, state=state)


@_flyte_cli.command('execute-launch-plan', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_optional_name_option
@_host_option
@_insecure_option
@_urn_option
@_principal_option
@_verbose_option
@_click.argument('lp_args', nargs=-1, type=_click.UNPROCESSED)
def execute_launch_plan(project, domain, name, host, insecure, urn, principal, verbose, lp_args):
    """
    Kick off a launch plan. Note that the {project, domain, name} specified in the command line
    will be for the execution.  The project/domain for the launch plan are specified in the urn.

    Use a -- to separate arguments to this cli, and arguments to the launch plan.
    e.g.
        $ flyte-cli -h localhost:30081 -p flyteexamples -d development execute-launch-plan \
            --verbose --principal=sdk-demo
            -u lp:flyteexamples:development:some-workflow:abc123 -- input=hi \
            other-input=123 moreinput=qwerty

    These arguments are then collected, and passed into the `lp_args` variable as a Tuple[Text].
    Users should use the get-launch-plan command to ascertain the names of inputs to use.
    """
    _welcome_message()

    with _platform_config.URL.get_patcher(host), _platform_config.INSECURE.get_patcher(_tt(insecure)):
        lp_id = _identifier.Identifier.from_python_std(urn)
        lp = _launch_plan_common.SdkLaunchPlan.fetch(lp_id.project, lp_id.domain, lp_id.name, lp_id.version)

        inputs = _construct_literal_map_from_parameter_map(lp.default_inputs, _parse_args_into_dict(lp_args))
        # TODO: Implement notification overrides
        # TODO: Implement label overrides
        # TODO: Implement annotation overrides
        execution = lp.execute_with_literals(project, domain, inputs, name=name)
        _click.secho("Launched execution: {}".format(_tt(execution.id)), fg='blue')
        _click.echo("")


########################################################################################################################
#
#  Execution Commands
#
########################################################################################################################

@_flyte_cli.command('relaunch-execution', cls=_FlyteSubCommand)
@_optional_project_option
@_optional_domain_option
@_optional_name_option
@_host_option
@_insecure_option
@_urn_option
@_optional_principal_option
@_verbose_option
@_click.argument('lp_args', nargs=-1, type=_click.UNPROCESSED)
def relaunch_execution(project, domain, name, host, insecure, urn, principal, verbose, lp_args):
    """
    Relaunch a launch plan.
    As with kicking off a launch plan (see execute-launch-plan), the project and domain will correspond to the new
    execution to be run, and the project/domain used to find the existing execution will come from the URN.
    This means you can re-run a development execution, in production, off of a staging launch-plan (in another project),
    but beware that execution environment configurations can result in slower executions or permissions failures.
    Therefore, it is recommended to re-run in the same environment as the original execution.  By default, if the
    project and domain are not specified, the existing project/domain will be used.

    When relaunching an execution, this will display the fixed inputs that it ran with (from the launch plan spec),
    and handle the other inputs similar to how we handle initial launch plan execution, except that
    all inputs now will have a default (the input of the execution being rerun).

    Use a -- to separate arguments to this cli, and arguments to the launch plan.
    e.g.
        $ flyte-cli -h localhost:30081 -p flyteexamples -d development execute-launch-plan \
            -u lp:flyteexamples:development:some-workflow:abc123 -- input=hi \
            other-input=123 moreinput=qwerty

    These arguments are then collected, and passed into the `lp_args` variable as a Tuple[Text].
    Users should use the get-execution and get-launch-plan commands to ascertain the names of inputs to use.
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Relaunching execution {}\n".format(_tt(urn)))
    existing_workflow_execution_identifier = _identifier.WorkflowExecutionIdentifier.from_python_std(urn)
    e = client.get_execution(existing_workflow_execution_identifier)

    if project is None:
        project = existing_workflow_execution_identifier.project
    if domain is None:
        domain = existing_workflow_execution_identifier.domain
    if principal is None:
        principal = e.spec.metadata.principal

    lp_model = client.get_launch_plan(e.spec.launch_plan)
    expected_inputs = lp_model.closure.expected_inputs

    # Parse text inputs using the LP closure's parameter map to determine types.  However, since all inputs are now
    # optional (because we can default to the original execution's), we reduce first to bare Variables.
    variable_map = {k: v.var for k, v in _six.iteritems(expected_inputs.parameters)}
    parsed_text_args = _parse_args_into_dict(lp_args)
    new_inputs = _construct_literal_map_from_variable_map(variable_map, parsed_text_args)
    if len(new_inputs.literals) > 0:
        _click.secho(
            "\tNew Inputs: {}\n".format(
                _prefix_lines("\t\t", _get_io_string(new_inputs, verbose=verbose))
            )
        )

    # Construct new inputs from existing execution inputs and new inputs
    inputs_dict = {}
    for k in e.spec.inputs.literals.keys():
        if k in new_inputs.literals:
            inputs_dict[k] = new_inputs.literals[k]
        else:
            inputs_dict[k] = e.spec.inputs.literals[k]
    inputs = _literals.LiteralMap(literals=inputs_dict)

    if len(inputs_dict) > 0:
        _click.secho(
            "\tFinal Inputs for New Execution: {}\n".format(
                _prefix_lines("\t\t", _get_io_string(inputs, verbose=verbose))
            )
        )

    metadata = _ExecutionMetadata(mode=_ExecutionMetadata.ExecutionMode.MANUAL, principal=principal, nesting=0)
    ex_spec = _ExecutionSpec(launch_plan=lp_model.id, inputs=inputs, metadata=metadata)
    execution_identifier = client.create_execution(project=project, domain=domain, name=name, execution_spec=ex_spec)
    execution_identifier = _identifier.WorkflowExecutionIdentifier.promote_from_model(execution_identifier)
    _click.secho("Launched execution: {}".format(execution_identifier), fg='blue')
    _click.echo("")


@_flyte_cli.command('terminate-execution', cls=_FlyteSubCommand)
@_host_option
@_insecure_option
@_cause_option
@_optional_urn_option
def terminate_execution(host, insecure, cause, urn=None):
    """
    Terminate an execution or a list of executions. This command terminates an execution
    specified by the URN. It can only terminate the executions the status of which are "RUNNING".
    The post-termination status of those executions will become "ABORTED".
    When terminating an execution, the cause of termination is a required input.

    This command also supports batch terminating multiple executions at a time, which can be
    achieved by supplying multiple URNs via the named pipe.

    Note that, the termination of executions might not take immediate effect, as the
    FlyteCLI only sends a termination request to FlyteAdmin. The actual termination
    of the execution(s) depends on many other factors such as the status of the
    machine serving the execution, etc.

    e.g.,
        $ flyte-cli -h localhost:30081 -p flyteexamples -d development terminate-execution \
            -u lp:flyteexamples:development:some-execution:abc123
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    _click.echo("Killing the following executions:\n")
    _click.echo("{:100} {:40}".format("Urn", "Cause"))

    # It first collects the urns in a list, and then send terminate request
    # for them one-by-one
    if urn is None:
        try:
            # Examine whether the input is from FIFO (named pipe)
            if _stat.S_ISFIFO(_os.fstat(0).st_mode):
                for line in _sys.stdin.readlines():
                    _terminate_one_execution(client, line.rstrip(), cause)
            else:
                # If the commandline parameter urn is not supplied, and neither
                # the input is from a pipe, it means the user is not using
                # this command appropriately
                raise _click.UsageError('Missing option "-u" / "--urn" or missing pipe inputs.')
        except KeyboardInterrupt:
            _sys.stdout.flush()
            pass
    else:
        _terminate_one_execution(client, urn, cause)


@_flyte_cli.command('list-executions', cls=_FlyteSubCommand)
@_project_option
@_domain_option
@_host_option
@_insecure_option
@_token_option
@_limit_option
@_show_all_option
@_filter_option
@_sort_by_option
@_optional_urns_only_option
def list_executions(project, domain, host, insecure, token, limit, show_all, filter, sort_by, urns_only):
    """
    List the key information of all the executions under the scope specified by {project, domain}.
    Users can supply additional filter arguments to show only the desired exeuctions.

    Note that, when the ``--urns-only`` flag is not set, this command prints out the complete tabular
    output with key pieces of information such as the URN, the Name and the Status of the executions;
    the column headers are also printed. If the flag is set, on the other hand, only the URNs
    of the executions will be printed. This will come in handy when the user wants to, for example, terminate all the
    running executions at once.
    """
    if not urns_only:
        _welcome_message()
        _click.echo("Executions Found in {}:{}\n".format(_tt(project), _tt(domain)))
        _click.echo("{:100} {:40} {:10}".format("Urn", "Name", "Status"))

    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)

    while True:
        exec_ids, next_token = client.list_executions_paginated(
            project,
            domain,
            limit=limit,
            token=token,
            filters=[_filters.Filter.from_python_std(f) for f in filter],
            sort_by=_admin_common.Sort.from_python_std(sort_by) if sort_by else None
        )
        for ex in exec_ids:
            _secho_one_execution(ex, urns_only)

        if show_all is not True:
            if next_token and not urns_only:
                _click.echo("Received next token: {}\n".format(next_token))
            break
        if not next_token:
            break
        token = next_token
    if not urns_only:
        _click.echo("")


def _get_io(node_executions, wf_execution, show_io, verbose):
    # Fetch I/O if necessary
    uri_to_message_map = {}
    if show_io:
        uris = [ne.input_uri for ne in node_executions]
        uris.extend([ne.closure.output_uri for ne in node_executions if ne.closure.output_uri is not None])
        if wf_execution is not None and \
                wf_execution.closure.outputs is not None and \
                wf_execution.closure.outputs.uri is not None:
            uris.append(wf_execution.closure.outputs.uri)

        with _click.progressbar(uris, label="Downloading Inputs and Outputs") as progress_bar_uris:
            for uri in progress_bar_uris:
                uri_to_message_map[uri] = _fetch_and_stringify_literal_map(uri, verbose=verbose)
    return uri_to_message_map


def _render_workflow_execution(wf_execution, uri_to_message_map, show_io, verbose):
    _click.echo(
        "\nExecution {project}:{domain}:{name}\n".format(
            project=_tt(wf_execution.id.project),
            domain=_tt(wf_execution.id.domain),
            name=_tt(wf_execution.id.name)
        )
    )
    _click.echo("\t{:15} ".format("State:"), nl=False)
    _secho_workflow_status(wf_execution.closure.phase)
    _click.echo(
        "\t{:15} {}".format(
            "Launch Plan:",
            _tt(_identifier.Identifier.promote_from_model(wf_execution.spec.launch_plan))
        )
    )

    if show_io:
        _click.secho(
            "\tInputs: {}\n".format(
                _prefix_lines("\t\t", _get_io_string(wf_execution.closure.computed_inputs, verbose=verbose))
            )
        )
        if wf_execution.closure.outputs is not None:
            if wf_execution.closure.outputs.uri:
                _click.secho(
                    "\tOutputs: {}\n".format(
                        _prefix_lines(
                            "\t\t",
                            uri_to_message_map.get(
                                wf_execution.closure.outputs.uri,
                                wf_execution.closure.outputs.uri
                            )
                        )
                    )
                )
            elif wf_execution.closure.outputs.values is not None:
                _click.secho(
                    "\tOutputs: {}\n".format(
                        _prefix_lines("\t\t", _get_io_string(wf_execution.closure.outputs.values, verbose=verbose))
                    )
                )
            else:
                _click.echo("\t{:15} (None)".format("Outputs:"))

    if wf_execution.closure.error is not None:
        _click.secho(_prefix_lines("\t", _render_error(wf_execution.closure.error)), fg='red', bold=True)


def _render_error(error):
    out = "Error:\n"
    out += "\tCode: {}\n".format(error.code)
    out += "\tMessage:\n"
    for l in error.message.splitlines():
        out += "\t\t{}".format(_tt(l))
    return out


def _get_all_task_executions_for_node(client, node_execution_identifier):
    fetched_task_execs = []
    token = ""
    while True:
        num_to_fetch = 100
        task_execs, next_token = client.list_task_executions_paginated(
            node_execution_identifier=node_execution_identifier,
            limit=num_to_fetch,
            token=token
        )
        for te in task_execs:
            fetched_task_execs.append(te)

        if not next_token:
            break
        token = next_token

    return fetched_task_execs


def _get_all_node_executions(client, workflow_execution_identifier=None, task_execution_identifier=None):
    all_node_execs = []
    token = ""
    while True:
        num_to_fetch = 100
        if workflow_execution_identifier:
            node_execs, next_token = client.list_node_executions(
                workflow_execution_identifier=workflow_execution_identifier,
                limit=num_to_fetch,
                token=token
            )
        else:
            node_execs, next_token = client.list_node_executions_for_task_paginated(
                task_execution_identifier=task_execution_identifier,
                limit=num_to_fetch,
                token=token,
            )
        all_node_execs.extend(node_execs)
        if not next_token:
            break
        token = next_token
    return all_node_execs


def _render_node_executions(client, node_execs, show_io, verbose, host, insecure, wf_execution=None):
    node_executions_to_task_executions = {}
    for node_exec in node_execs:
        node_executions_to_task_executions[node_exec.id] = _get_all_task_executions_for_node(client, node_exec.id)

    uri_to_message_map = _get_io(node_execs, wf_execution, show_io, verbose)
    if wf_execution is not None:
        _render_workflow_execution(wf_execution, uri_to_message_map, show_io, verbose)

    _click.echo("\n\tNode Executions:\n")
    for ne in sorted(node_execs, key=lambda x: x.closure.started_at):
        if ne.id.node_id == 'start-node':
            continue
        _click.echo("\t\tID: {}\n".format(_tt(ne.id.node_id)))
        _click.echo("\t\t\t{:15} ".format("Status:"), nl=False)
        _secho_node_execution_status(ne.closure.phase)
        _click.echo("\t\t\t{:15} {:60} ".format("Started:", _tt(ne.closure.started_at)))
        _click.echo("\t\t\t{:15} {:60} ".format("Duration:", _tt(ne.closure.duration)))
        _click.echo(
            "\t\t\t{:15} {}".format(
                "Input:",
                _prefix_lines("\t\t\t{:15} ".format(""), uri_to_message_map.get(ne.input_uri, ne.input_uri))
            )
        )
        if ne.closure.output_uri:
            _click.echo(
                "\t\t\t{:15} {}".format(
                    "Output:",
                    _prefix_lines(
                        "\t\t\t{:15} ".format(""),
                        uri_to_message_map.get(ne.closure.output_uri, ne.closure.output_uri)
                    )
                )
            )
        if ne.closure.error is not None:
            _click.secho(
                _prefix_lines(
                    "\t\t\t",
                    _render_error(ne.closure.error)
                ),
                bold=True,
                fg='red'
            )

        task_executions = node_executions_to_task_executions.get(ne.id, [])
        if len(task_executions) > 0:
            _click.echo("\n\t\t\tTask Executions:\n")
            for te in sorted(task_executions, key=lambda x: x.id.retry_attempt):
                _click.echo("\t\t\t\tAttempt {}:\n".format(te.id.retry_attempt))
                _click.echo("\t\t\t\t\t{:15} {:60} ".format("Created:", _tt(te.closure.created_at)))
                _click.echo("\t\t\t\t\t{:15} {:60} ".format("Started:", _tt(te.closure.started_at)))
                _click.echo("\t\t\t\t\t{:15} {:60} ".format("Updated:", _tt(te.closure.updated_at)))
                _click.echo("\t\t\t\t\t{:15} {:60} ".format("Duration:", _tt(te.closure.duration)))
                _click.echo("\t\t\t\t\t{:15} ".format("Status:"), nl=False)
                _secho_task_execution_status(te.closure.phase)
                if len(te.closure.logs) == 0:
                    _click.echo("\t\t\t\t\t{:15} {:60} ".format("Logs:", "(None Found Yet)"))
                else:
                    _click.echo("\t\t\t\t\tLogs:\n")
                    for log in sorted(te.closure.logs, key=lambda x: x.name):
                        _click.echo("\t\t\t\t\t\t{:8} {}".format("Name:", log.name))
                        _click.echo("\t\t\t\t\t\t{:8} {}\n".format("URI:", log.uri))

                if te.closure.error is not None:
                    _click.secho(
                        _prefix_lines(
                            "\t\t\t\t\t",
                            _render_error(te.closure.error)
                        ),
                        bold=True,
                        fg='red'
                    )

                if te.is_parent:
                    _click.echo(
                        "\t\t\t\t\t{:15} {:60} ".format(
                            "Subtasks:",
                            "flyte-cli get-child-executions -h {host}{insecure} -u {urn}".format(
                                host=host,
                                urn=_tt(_identifier.TaskExecutionIdentifier.promote_from_model(te.id)),
                                insecure=" --insecure" if insecure else ""
                            )
                        )
                    )
            _click.echo()
        _click.echo()
    _click.echo()


@_flyte_cli.command('get-execution', cls=_FlyteSubCommand)
@_urn_option
@_host_option
@_insecure_option
@_show_io_option
@_verbose_option
def get_execution(urn, host, insecure, show_io, verbose):
    """
    Get the detail information of a certain execution identified by the URN of that launch plan.
    The URN of an execution is in the form of ``ex:<project>:<domain>:<execution_name>``
    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)
    e = client.get_execution(_identifier.WorkflowExecutionIdentifier.from_python_std(urn))
    node_execs = _get_all_node_executions(client, workflow_execution_identifier=e.id)
    _render_node_executions(client, node_execs, show_io, verbose, host, insecure, wf_execution=e)


@_flyte_cli.command('get-child-executions', cls=_FlyteSubCommand)
@_urn_option
@_host_option
@_insecure_option
@_show_io_option
@_verbose_option
def get_child_executions(urn, host, insecure, show_io, verbose):
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)
    node_execs = _get_all_node_executions(
        client,
        task_execution_identifier=_identifier.TaskExecutionIdentifier.from_python_std(urn)
    )
    _render_node_executions(client, node_execs, show_io, verbose, host, insecure)


@_flyte_cli.command('register-project', cls=_FlyteSubCommand)
@_project_identifier_option
@_project_name_option
@_host_option
@_insecure_option
def register_project(identifier, name, host, insecure):
    """
    Register a new project.

    """
    _welcome_message()
    client = _friendly_client.SynchronousFlyteClient(host, insecure=insecure)
    client.register_project(_Project(identifier, name))
    _click.echo("Registered project [id: {}, name: {}]".format(identifier, name))


if __name__ == "__main__":
    _flyte_cli()
