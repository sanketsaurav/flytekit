from __future__ import absolute_import

import logging as _logging
import os as _os
import traceback as _traceback
from datetime import datetime as _datetime

import six as _six

from flytekit.clients.helpers import iterate_node_executions as _iterate_node_executions, iterate_task_executions as \
    _iterate_task_executions
from flytekit import __version__ as _api_version
from flytekit.clients.friendly import SynchronousFlyteClient as _SynchronousFlyteClient
from flytekit.common import utils as _common_utils, constants as _constants
from flytekit.common.exceptions import user as _user_exceptions, scopes as _exception_scopes
from flytekit.configuration import platform as _platform_config, internal as _internal_config, sdk as _sdk_config
from flytekit.engines import common as _common_engine
from flytekit.interfaces.data import data_proxy as _data_proxy
from flytekit.interfaces.stats.taggable import get_stats as _get_stats
from flytekit.models import task as _task_models, execution as _execution_models, \
    literals as _literals
from flytekit.models.admin import workflow as _workflow_model
from flytekit.models.core import errors as _error_models
from flytekit.models.core.identifier import WorkflowExecutionIdentifier
from flyteidl.core import literals_pb2 as _literals_pb2


class _FlyteClientManager(object):

    _CLIENT = None

    def __init__(self, *args, **kwargs):
        # TODO: React to changing configs.  For now this is frozen for the lifetime of the process, which covers most
        # TODO: use cases.
        if type(self)._CLIENT is None:
            type(self)._CLIENT = _SynchronousFlyteClient(*args, **kwargs)

    @property
    def client(self):
        """
        :rtype: flytekit.clients.friendly.SynchronousFlyteClient
        """
        return type(self)._CLIENT


class FlyteEngineFactory(_common_engine.BaseExecutionEngineFactory):

    def get_workflow(self, sdk_workflow):
        """
        :param flytekit.common.workflow.SdkWorkflow sdk_workflow:
        :rtype: FlyteWorkflow
        """
        return FlyteWorkflow(sdk_workflow)

    def get_task(self, sdk_task):
        """
        :param flytekit.common.tasks.task.SdkTask sdk_task:
        :rtype: FlyteTask
        """
        return FlyteTask(sdk_task)

    def get_launch_plan(self, sdk_launch_plan):
        """
        :param flytekit.common.launch_plan.SdkLaunchPlan sdk_launch_plan:
        :rtype: FlyteLaunchPlan
        """
        return FlyteLaunchPlan(sdk_launch_plan)

    def get_task_execution(self, task_exec):
        """
        :param flytekit.common.tasks.executions.SdkTaskExecution task_exec:
        :rtype: FlyteTaskExecution
        """
        return FlyteTaskExecution(task_exec)

    def get_node_execution(self, node_exec):
        """
        :param flytekit.common.nodes.SdkNodeExecution node_exec:
        :rtype: FlyteNodeExecution
        """
        return FlyteNodeExecution(node_exec)

    def get_workflow_execution(self, wf_exec):
        """
        :param flytekit.common.workflow_execution.SdkWorkflowExecution wf_exec:
        :rtype: FlyteWorkflowExecution
        """
        return FlyteWorkflowExecution(wf_exec)

    def fetch_workflow_execution(self, wf_exec_id):
        """
        :param flytekit.models.core.identifier.WorkflowExecutionIdentifier wf_exec_id:
        :rtype: flytekit.models.execution.Execution
        """
        return _FlyteClientManager(
            _platform_config.URL.get(),
            insecure=_platform_config.INSECURE.get()
        ).client.get_execution(wf_exec_id)

    def fetch_task(self, task_id):
        """
        Queries Admin for an existing Admin task
        :param flytekit.models.core.identifier.Identifier task_id:
        :rtype: flytekit.models.task.Task
        """
        return _FlyteClientManager(
            _platform_config.URL.get(),
            insecure=_platform_config.INSECURE.get()
        ).client.get_task(task_id)

    def fetch_launch_plan(self, launch_plan_id):
        """
        :param flytekit.models.core.identifier.Identifier launch_plan_id: This identifier should have a resource
            type of kind LaunchPlan.
        :rtype: flytekit.models.launch_plan.LaunchPlan
        """
        return _FlyteClientManager(
            _platform_config.URL.get(),
            insecure=_platform_config.INSECURE.get()
        ).client.get_launch_plan(launch_plan_id)

    def fetch_workflow(self, workflow_id):
        """
        :param flytekit.models.core.identifier.Identifier workflow_id: This identifier should have a resource
            type of kind LaunchPlan.
        :rtype: flytekit.models.admin.workflow.Workflow
        """
        return _FlyteClientManager(
            _platform_config.URL.get(),
            insecure=_platform_config.INSECURE.get()
        ).client.get_workflow(workflow_id)


class FlyteLaunchPlan(_common_engine.BaseLaunchPlanExecutor):

    def register(self, identifier):
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        try:
            client.create_launch_plan(
                identifier,
                self.sdk_launch_plan
            )
        except _user_exceptions.FlyteEntityAlreadyExistsException:
            pass

    def execute(self, project, domain, name, inputs, notification_overrides=None, label_overrides=None,
                annotation_overrides=None):
        """
        Executes the launch plan.
        :param Text project:
        :param Text domain:
        :param Text name:
        :param flytekit.models.literals.LiteralMap inputs:
        :param list[flytekit.models.common.Notification] notification_overrides: If specified, override the
            notifications.
        :param flytekit.models.common.Labels label_overrides:
        :param flytekit.models.common.Annotations annotation_overrides:
        :rtype: flytekit.models.execution.Execution
        """
        disable_all = (notification_overrides == [])
        if disable_all:
            notification_overrides = None
        else:
            notification_overrides = _execution_models.NotificationList(
                notification_overrides or []
            )
            disable_all = None

        # TODO: Handle idempotency when admin is prepared.
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        exec_id = client.create_execution(
            project,
            domain,
            name,
            _execution_models.ExecutionSpec(
                self.sdk_launch_plan.id,
                inputs,
                _execution_models.ExecutionMetadata(
                    _execution_models.ExecutionMetadata.ExecutionMode.MANUAL,
                    'sdk',  # TODO: get principle
                    0  # TODO: Detect nesting
                ),
                notifications=notification_overrides,
                disable_all=disable_all,
                labels=label_overrides,
                annotations=annotation_overrides,
            )
        )
        return client.get_execution(exec_id)

    def update(self, identifier, state):
        """
        :param flytekit.models.core.identifier.Identifier identifier: Identifier for launch plan to update
        :param int state: Enum value from flytekit.models.launch_plan.LaunchPlanState
        """
        return _FlyteClientManager(
            _platform_config.URL.get(),
            insecure=_platform_config.INSECURE.get()
        ).client.update_launch_plan(identifier, state)


class FlyteWorkflow(_common_engine.BaseWorkflowExecutor):

    def register(self, identifier):
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        try:
            return client.create_workflow(
                identifier,
                _workflow_model.WorkflowSpec(self.sdk_workflow)
            )
        except _user_exceptions.FlyteEntityAlreadyExistsException:
            pass


class FlyteTask(_common_engine.BaseTaskExecutor):

    def register(self, identifier):
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        try:
            client.create_task(
                identifier,
                _task_models.TaskSpec(
                    self.sdk_task
                )
            )
        except _user_exceptions.FlyteEntityAlreadyExistsException:
            pass

    def execute(self, inputs, context=None):
        """
        Just execute the task and write the outputs to where they belong
        :param flytekit.models.literals.LiteralMap inputs:
        :param dict[Text, Text] context:
        :rtype: dict[Text, flytekit.models.common.FlyteIdlEntity]
        """

        with _common_utils.AutoDeletingTempDir("engine_dir") as temp_dir:
            with _common_utils.AutoDeletingTempDir("task_dir") as task_dir:
                with _data_proxy.LocalWorkingDirectoryContext(task_dir):
                    with _data_proxy.RemoteDataContext():
                        output_file_dict = dict()

                        # This sets the logging level for user code and is the only place an sdk setting gets
                        # used at runtime.  Optionally, Propeller can set an internal config setting which
                        # takes precedence.
                        log_level = _internal_config.LOGGING_LEVEL.get() or _sdk_config.LOGGING_LEVEL.get()
                        _logging.getLogger().setLevel(log_level)

                        try:
                            output_file_dict = self.sdk_task.execute(
                                _common_engine.EngineContext(
                                    execution_id=WorkflowExecutionIdentifier(
                                        project=_internal_config.EXECUTION_PROJECT.get(),
                                        domain=_internal_config.EXECUTION_DOMAIN.get(),
                                        name=_internal_config.EXECUTION_NAME.get()
                                    ),
                                    execution_date=_datetime.utcnow(),
                                    stats=_get_stats(
                                        # Stats metric path will be:
                                        # registration_project.registration_domain.app.module.task_name.user_stats
                                        # and it will be tagged with execution-level values for project/domain/wf/lp
                                        "{}.{}.{}.user_stats".format(
                                            _internal_config.TASK_PROJECT.get() or _internal_config.PROJECT.get(),
                                            _internal_config.TASK_DOMAIN.get() or _internal_config.DOMAIN.get(),
                                            _internal_config.TASK_NAME.get() or _internal_config.NAME.get()
                                        ),
                                        tags={
                                            'exec_project': _internal_config.EXECUTION_PROJECT.get(),
                                            'exec_domain': _internal_config.EXECUTION_DOMAIN.get(),
                                            'exec_workflow': _internal_config.EXECUTION_WORKFLOW.get(),
                                            'exec_launchplan': _internal_config.EXECUTION_LAUNCHPLAN.get(),
                                            'api_version': _api_version
                                        }
                                    ),
                                    logging=_logging,
                                    tmp_dir=task_dir
                                ),
                                inputs
                            )
                        except _exception_scopes.FlyteScopedException as e:
                            _logging.error("!!! Begin Error Captured by Flyte !!!")
                            output_file_dict[_constants.ERROR_FILE_NAME] = _error_models.ErrorDocument(
                                _error_models.ContainerError(
                                    e.error_code,
                                    e.verbose_message,
                                    e.kind
                                )
                            )
                            _logging.error(e.verbose_message)
                            _logging.error("!!! End Error Captured by Flyte !!!")
                        except Exception:
                            _logging.error("!!! Begin Unknown System Error Captured by Flyte !!!")
                            exc_str = _traceback.format_exc()
                            output_file_dict[_constants.ERROR_FILE_NAME] = _error_models.ErrorDocument(
                                _error_models.ContainerError(
                                    "SYSTEM:Unknown",
                                    exc_str,
                                    _error_models.ContainerError.Kind.RECOVERABLE
                                )
                            )
                            _logging.error(exc_str)
                            _logging.error("!!! End Error Captured by Flyte !!!")
                        finally:
                            for k, v in _six.iteritems(output_file_dict):
                                _common_utils.write_proto_to_file(
                                    v.to_flyte_idl(),
                                    _os.path.join(temp_dir.name, k)
                                )
                            _data_proxy.Data.put_data(temp_dir.name, context['output_prefix'], is_multipart=True)


class FlyteWorkflowExecution(_common_engine.BaseWorkflowExecution):

    def get_node_executions(self, filters=None):
        """
        :param list[flytekit.models.filters.Filter] filters:
        :rtype: dict[Text, flytekit.common.nodes.SdkNodeExecution]
        """
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        return {
            v.id.node_id: v
            for v in _iterate_node_executions(client, self.sdk_workflow_execution.id, filters=filters)
        }

    def sync(self):
        """
        :rtype: None
        """
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        self.sdk_workflow_execution._closure = client.get_execution(self.sdk_workflow_execution.id).closure

    def get_inputs(self):
        """
        :rtype: flytekit.models.literals.LiteralMap
        """
        return self.sdk_workflow_execution.closure.computed_inputs

    def get_outputs(self):
        """
        :rtype: flytekit.models.literals.LiteralMap
        """
        if self.sdk_workflow_execution.closure.outputs.values:
            return self.sdk_workflow_execution.closure.outputs.values
        else:
            with _common_utils.AutoDeletingTempDir() as t:
                tmp_name = _os.path.join(t.name, "outputs.pb")
                _data_proxy.Data.get_data(self.sdk_workflow_execution.closure.outputs.uri, tmp_name)
                return _literals.LiteralMap.from_flyte_idl(
                    _common_utils.load_proto_from_file(_literals_pb2.LiteralMap, tmp_name)
                )

    def terminate(self, cause):
        """
        :param Text cause:
        """
        _FlyteClientManager(
            _platform_config.URL.get(),
            insecure=_platform_config.INSECURE.get()
        ).client.terminate_execution(self.sdk_workflow_execution.id, cause)


class FlyteNodeExecution(_common_engine.BaseNodeExecution):

    def get_task_executions(self):
        """
        :rtype: list[flytekit.common.tasks.executions.SdkTaskExecution]
        """
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        return list(_iterate_task_executions(client, self.sdk_node_execution.id))

    def get_subworkflow_executions(self):
        """
        :rtype: list[flytekit.common.workflow_execution.SdkWorkflowExecution]
        """
        raise NotImplementedError("Cannot retrieve sub-workflopw information from a node execution yet.")

    def get_inputs(self):
        """
        :rtype: flytekit.models.literals.LiteralMap
        """
        with _common_utils.AutoDeletingTempDir() as t:
            tmp_name = _os.path.join(t.name, "inputs.pb")
            _data_proxy.Data.get_data(self.sdk_node_execution.input_uri, tmp_name)
            return _literals.LiteralMap.from_flyte_idl(
                _common_utils.load_proto_from_file(_literals_pb2.LiteralMap, tmp_name)
            )

    def get_outputs(self):
        """
        :rtype: flytekit.models.literals.LiteralMap
        """
        with _common_utils.AutoDeletingTempDir() as t:
            tmp_name = _os.path.join(t.name, "outputs.pb")
            _data_proxy.Data.get_data(self.sdk_node_execution.closure.output_uri, tmp_name)
            return _literals.LiteralMap.from_flyte_idl(
                _common_utils.load_proto_from_file(_literals_pb2.LiteralMap, tmp_name)
            )

    def sync(self):
        """
        :rtype: None
        """
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        self.sdk_node_execution._closure = client.get_node_execution(self.sdk_node_execution.id).closure


class FlyteTaskExecution(_common_engine.BaseTaskExecution):

    def get_inputs(self):
        """
        :rtype: flytekit.models.literals.LiteralMap
        """
        with _common_utils.AutoDeletingTempDir() as t:
            tmp_name = _os.path.join(t.name, "inputs.pb")
            _data_proxy.Data.get_data(self.sdk_task_execution.input_uri, tmp_name)
            return _literals.LiteralMap.from_flyte_idl(
                _common_utils.load_proto_from_file(_literals_pb2.LiteralMap, tmp_name)
            )

    def get_outputs(self):
        """
        :rtype: flytekit.models.literals.LiteralMap
        """
        with _common_utils.AutoDeletingTempDir() as t:
            tmp_name = _os.path.join(t.name, "outputs.pb")
            _data_proxy.Data.get_data(self.sdk_task_execution.closure.output_uri, tmp_name)
            return _literals.LiteralMap.from_flyte_idl(
                _common_utils.load_proto_from_file(_literals_pb2.LiteralMap, tmp_name)
            )

    def sync(self):
        """
        :rtype: None
        """
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        self.sdk_task_execution._closure = client.get_task_execution(self.sdk_task_execution.id).closure

    def get_child_executions(self, filters=None):
        """
        :param list[flytekit.models.filters.Filter] filters:
        :rtype: dict[Text, flytekit.common.nodes.SdkNodeExecution]
        """
        client = _FlyteClientManager(_platform_config.URL.get(), insecure=_platform_config.INSECURE.get()).client
        return {
            v.id.node_id: v
            for v in _iterate_node_executions(
                client,
                task_execution_identifier=self.sdk_task_execution.id,
                filters=filters
            )
        }
