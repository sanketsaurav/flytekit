from __future__ import absolute_import

import six as _six

from flyteidl.admin import task_pb2 as _task_pb2, common_pb2 as _common_pb2, workflow_pb2 as _workflow_pb2, \
    launch_plan_pb2 as _launch_plan_pb2, execution_pb2 as _execution_pb2, node_execution_pb2 as _node_execution_pb2, \
    task_execution_pb2 as _task_execution_pb2, project_pb2 as _project_pb2

from flytekit.clients.raw import RawSynchronousFlyteClient as _RawSynchronousFlyteClient
from flytekit.models import filters as _filters, common as _common, launch_plan as _launch_plan, task as _task, \
    execution as _execution, node_execution as _node_execution
from flytekit.models.core import identifier as _identifier
from flytekit.models.admin import workflow as _workflow, task_execution as _task_execution


class SynchronousFlyteClient(_RawSynchronousFlyteClient):

    ####################################################################################################################
    #
    #  Task Endpoints
    #
    ####################################################################################################################

    def create_task(
            self,
            task_identifer,
            task_spec
    ):
        """
        This will create a task definition in the Admin database. Once successful, the task object can be
        retrieved via the client or viewed via the UI or command-line interfaces.

        .. note ::

            Overwrites are not supported so any request for a given project, domain, name, and version that exists in
            the database must match the existing definition exactly. Furthermore, as long as the request
            remains identical, calling this method multiple times will result in success.

        :param flytekit.models.core.identifier.Identifier task_identifer: The identifier for this task.
        :param flytekit.models.task.TaskSpec task_spec: This is the actual definition of the task that
            should be created.
        :raises flytekit.common.exceptions.user.FlyteEntityAlreadyExistsException: If an identical version of the
            task is found, this exception is raised.  The client might choose to ignore this exception because the
            identical task is already registered.
        :raises grpc.RpcError:
        """
        super(SynchronousFlyteClient, self).create_task(
            _task_pb2.TaskCreateRequest(
                id=task_identifer.to_flyte_idl(),
                spec=task_spec.to_flyte_idl()
            )
        )

    def list_task_ids_paginated(
            self,
            project,
            domain,
            limit=100,
            token=None,
            sort_by=None
    ):
        """
        This returns a page of identifiers for the tasks for a given project and domain. Filters can also be
        specified.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param Text project: The namespace of the project to list.
        :param Text domain: The domain space of the project to list.
        :param int limit: [Optional] The maximum number of entries to return.  Must be greater than 0.  The maximum
            page size is determined by the Flyte Admin Service configuration.  If limit is greater than the maximum
            page size, an exception will be raised.
        :param Text token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
            If you previously retrieved a page response with token="foo" and you want the next page,
            specify token="foo". Please see the notes for this function about the caveats of the paginated API.
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :raises: TODO
        :rtype: list[flytekit.models.common.NamedEntityIdentifier], Text
        """
        identifier_list = super(SynchronousFlyteClient, self).list_task_ids_paginated(
            _common_pb2.NamedEntityIdentifierListRequest(
                project=project,
                domain=domain,
                limit=limit,
                token=token,
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        return [
                   _common.NamedEntityIdentifier.from_flyte_idl(identifier_pb)
                   for identifier_pb in identifier_list.entities
               ], _six.text_type(identifier_list.token)

    def list_tasks_paginated(
            self,
            identifier,
            limit=100,
            token=None,
            filters=None,
            sort_by=None
    ):
        """
        This returns a page of task metadata for tasks in a given project and domain.  Optionally,
        specifying a name will limit the results to only tasks with that name in the given project and domain.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param flytekit.models.common.NamedEntityIdentifier identifier: NamedEntityIdentifier to list.
        :param int limit: [Optional] The maximum number of entries to return.  Must be greater than 0.  The maximum
            page size is determined by the Flyte Admin Service configuration.  If limit is greater than the maximum
            page size, an exception will be raised.
        :param int token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
            If you previously retrieved a page response with token="foo" and you want the next page,
            specify token="foo". Please see the notes for this function about the caveats of the paginated API.
        :param list[flytekit.models.filters.Filter] filters: [Optional] If specified, the filters will be applied to
            the query.  If the filter is not supported, an exception will be raised.
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :raises: TODO
        :rtype: list[flytekit.models.task.Task], Text
        """
        task_list = super(SynchronousFlyteClient, self).list_tasks_paginated(
            resource_list_request=_common_pb2.ResourceListRequest(
                id=identifier.to_flyte_idl(),
                limit=limit,
                token=token,
                filters=_filters.FilterList(filters or []).to_flyte_idl(),
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        # TODO: tmp workaround
        for pb in task_list.tasks:
            pb.id.resource_type = _identifier.ResourceType.TASK
        return [_task.Task.from_flyte_idl(task_pb2) for task_pb2 in task_list.tasks], _six.text_type(task_list.token)

    def get_task(self, id):
        """
        This returns a single task for a given identifier.

        :param flytekit.models.core.identifier.Identifier id: The ID representing a given task.
        :raises: TODO
        :rtype: flytekit.models.task.Task
        """
        return _task.Task.from_flyte_idl(
            super(SynchronousFlyteClient, self).get_task(
                _common_pb2.ObjectGetRequest(
                    id=id.to_flyte_idl()
                )
            )
        )

    ####################################################################################################################
    #
    #  Workflow Endpoints
    #
    ####################################################################################################################

    def create_workflow(
            self,
            workflow_identifier,
            workflow_spec
    ):
        """
        This will create a workflow definition in the Admin database. Once successful, the workflow object can be
        retrieved via the client or viewed via the UI or command-line interfaces.

        .. note ::

            Overwrites are not supported so any request for a given project, domain, name, and version that exists in
            the database must match the existing definition exactly. Furthermore, as long as the request
            remains identical, calling this method multiple times will result in success.

        :param: flytekit.models.core.identifier.Identifier workflow_identifier: The identifier for this workflow.
        :param: Text version: The version identifier of this workflow. Used to distinguish between different iterations
            of tasks with the same name. If any aspect of the underlying workflow definition changes, then the version
            must also change to be accepted by the Flyte Admin Service.
        :param: flytekit.models.admin.workflow.WorkflowSpec workflow_spec: This is the actual definition of the workflow
            that should be created.
        :raises flytekit.common.exceptions.user.FlyteEntityAlreadyExistsException: If an identical version of the
            workflow is found, this exception is raised.  The client might choose to ignore this exception because the
            identical workflow is already registered.
        :raises grpc.RpcError:
        """
        super(SynchronousFlyteClient, self).create_workflow(
            _workflow_pb2.WorkflowCreateRequest(
                id=workflow_identifier.to_flyte_idl(),
                spec=workflow_spec.to_flyte_idl()
            )
        )

    def list_workflow_ids_paginated(
            self,
            project,
            domain,
            limit=100,
            token=None,
            sort_by=None
    ):
        """
        This returns a page of identifiers for the workflows for a given project and domain. Filters can also be
        specified.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param: Text project: The namespace of the project to list.
        :param: Text domain: The domain space of the project to list.
        :param: int limit: [Optional] The maximum number of entries to return.  Must be greater than 0.  The maximum
            page size is determined by the Flyte Admin Service configuration.  If limit is greater than the maximum
            page size, an exception will be raised.
        :param: int token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
            If you previously retrieved a page response with token="foo" and you want the next page,
            specify token="foo". Please see the notes for this function about the caveats of the paginated API.
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :raises: TODO
        :rtype: list[flytekit.models.common.NamedEntityIdentifier], Text
        """
        identifier_list = super(SynchronousFlyteClient, self).list_workflow_ids_paginated(
            _common_pb2.NamedEntityIdentifierListRequest(
                project=project,
                domain=domain,
                limit=limit,
                token=token,
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        return [
                   _common.NamedEntityIdentifier.from_flyte_idl(identifier_pb)
                   for identifier_pb in identifier_list.entities
               ], _six.text_type(identifier_list.token)

    def list_workflows_paginated(
            self,
            identifier,
            limit=100,
            token=None,
            filters=None,
            sort_by=None
    ):
        """
        This returns a page of workflow meta-information for workflows in a given project and domain.  Optionally,
        specifying a name will limit the results to only workflows with that name in the given project and domain.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param flytekit.models.common.NamedEntityIdentifier identifier: NamedEntityIdentifier to list.
        :param int limit: [Optional] The maximum number of entries to return.  Must be greater than 0.  The maximum
            page size is determined by the Flyte Admin Service configuration.  If limit is greater than the maximum
            page size, an exception will be raised.
        :param int token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
            If you previously retrieved a page response with token="foo" and you want the next page,
            specify token="foo". Please see the notes for this function about the caveats of the paginated API.
        :param list[flytekit.models.filters.Filter] filters: [Optional] If specified, the filters will be applied to
            the query.  If the filter is not supported, an exception will be raised.
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :raises: TODO
        :rtype: list[flytekit.models.admin.workflow.Workflow], Text
        """
        wf_list = super(SynchronousFlyteClient, self).list_workflows_paginated(
            resource_list_request=_common_pb2.ResourceListRequest(
                id=identifier.to_flyte_idl(),
                limit=limit,
                token=token,
                filters=_filters.FilterList(filters or []).to_flyte_idl(),
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        # TODO: tmp workaround
        for pb in wf_list.workflows:
            pb.id.resource_type = _identifier.ResourceType.WORKFLOW
        return [_workflow.Workflow.from_flyte_idl(wf_pb2) for wf_pb2 in wf_list.workflows], \
            _six.text_type(wf_list.token)

    def get_workflow(self, id):
        """
        This returns a single task for a given ID.

        :param flytekit.models.core.identifier.Identifier id: The ID representing a given task.
        :raises: TODO
        :rtype: flytekit.models.admin.workflow.Workflow
        """
        return _workflow.Workflow.from_flyte_idl(
            super(SynchronousFlyteClient, self).get_workflow(
                _common_pb2.ObjectGetRequest(
                    id=id.to_flyte_idl()
                )
            )
        )

    ####################################################################################################################
    #
    #  Launch Plan Endpoints
    #
    ####################################################################################################################

    def create_launch_plan(
            self,
            launch_plan_identifer,
            launch_plan_spec
    ):
        """
        This will create a launch plan definition in the Admin database.  Once successful, the launch plan object can be
        retrieved via the client or viewed via the UI or command-line interfaces.

        .. note ::

            Overwrites are not supported so any request for a given project, domain, name, and version that exists in
            the database must match the existing definition exactly.  This also means that as long as the request
            remains identical, calling this method multiple times will result in success.

        :param: flytekit.models.core.identifier.Identifier launch_plan_identifer: The identifier for this launch plan.
        :param: Text version: The version identifier of this launch plan. Used to distinguish between different
            iterations of tasks with the same name. If any aspect of the underlying launch plan definition changes,
            then the version must also change to be accepted by the Flyte Admin Service.
        :param: flytekit.models.launch_plan.LaunchPlanSpec launch_plan_spec: This is the actual definition of the
            launch plan that should be created.
        :raises flytekit.common.exceptions.user.FlyteEntityAlreadyExistsException: If an identical version of the
            launch plan is found, this exception is raised.  The client might choose to ignore this exception because
            the identical launch plan is already registered.
        :raises grpc.RpcError:
        """
        super(SynchronousFlyteClient, self).create_launch_plan(
            _launch_plan_pb2.LaunchPlanCreateRequest(
                id=launch_plan_identifer.to_flyte_idl(),
                spec=launch_plan_spec.to_flyte_idl()
            )
        )

    def get_launch_plan(self, id):
        """
        Retrieves a launch plan entity.

        :param flytekit.models.core.identifier.Identifier id: unique identifier for launch plan to retrieve
        :rtype: flytekit.models.launch_plan.LaunchPlan
        """
        return _launch_plan.LaunchPlan.from_flyte_idl(
            super(SynchronousFlyteClient, self).get_launch_plan(
                _common_pb2.ObjectGetRequest(
                    id=id.to_flyte_idl()
                )
            )
        )

    def list_launch_plan_ids_paginated(
            self,
            project,
            domain,
            limit=100,
            token=None,
            sort_by=None
    ):
        """
        This returns a page of identifiers for the launch plans for a given project and domain. Filters can also be
        specified.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param: Text project: The namespace of the project to list.
        :param: Text domain: The domain space of the project to list.
        :param: int limit: [Optional] The maximum number of entries to return.  Must be greater than 0.  The maximum
            page size is determined by the Flyte Admin Service configuration.  If limit is greater than the maximum
            page size, an exception will be raised.
        :param: int token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
            If you previously retrieved a page response with token="foo" and you want the next page,
            specify token="foo". Please see the notes for this function about the caveats of the paginated API.
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :raises: TODO
        :rtype: list[flytekit.models.common.NamedEntityIdentifier], Text
        """
        identifier_list = super(SynchronousFlyteClient, self).list_launch_plan_ids_paginated(
            _common_pb2.NamedEntityIdentifierListRequest(
                project=project,
                domain=domain,
                limit=limit,
                token=token,
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        return [
                   _common.NamedEntityIdentifier.from_flyte_idl(identifier_pb)
                   for identifier_pb in identifier_list.entities
               ], _six.text_type(identifier_list.token)

    def list_launch_plans_paginated(
            self,
            identifier,
            limit=100,
            token=None,
            filters=None,
            sort_by=None
    ):
        """
        This returns a page of launch plan meta-information for launch plans in a given project and domain.  Optionally,
        specifying a name will limit the results to only workflows with that name in the given project and domain.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param flytekit.models.common.NamedEntityIdentifier identifier: NamedEntityIdentifier to list.
        :param int limit: [Optional] The maximum number of entries to return.  Must be greater than 0.  The maximum
            page size is determined by the Flyte Admin Service configuration.  If limit is greater than the maximum
            page size, an exception will be raised.
        :param int token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
            If you previously retrieved a page response with token="foo" and you want the next page,
            specify token="foo". Please see the notes for this function about the caveats of the paginated API.
        :param list[flytekit.models.filters.Filter] filters: [Optional] If specified, the filters will be applied to
            the query.  If the filter is not supported, an exception will be raised.
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :raises: TODO
        :rtype: list[flytekit.models.launch_plan.LaunchPlan], str
        """
        lp_list = super(SynchronousFlyteClient, self).list_launch_plans_paginated(
            resource_list_request=_common_pb2.ResourceListRequest(
                id=identifier.to_flyte_idl(),
                limit=limit,
                token=token,
                filters=_filters.FilterList(filters or []).to_flyte_idl(),
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        # TODO: tmp workaround
        for pb in lp_list.launch_plans:
            pb.id.resource_type = _identifier.ResourceType.LAUNCH_PLAN
        return [_launch_plan.LaunchPlan.from_flyte_idl(pb) for pb in lp_list.launch_plans], \
            _six.text_type(lp_list.token)

    def update_launch_plan(self, id, state):
        """
        Updates a launch plan.  Currently, this can only be used to update a given launch plan's state (ACTIVE v.
        INACTIVE) for schedules.  If a launch plan with a given project, domain, and name is set to ACTIVE,
        then any other launch plan with the same project, domain, and name that was set to ACTIVE will be switched to
        INACTIVE in one transaction.

        :param flytekit.models.core.identifier.Identifier id: identifier for launch plan to update
        :param int state: Enum value from flytekit.models.launch_plan.LaunchPlanState
        """
        super(SynchronousFlyteClient, self).update_launch_plan(
            _launch_plan_pb2.LaunchPlanUpdateRequest(
                id=id.to_flyte_idl(),
                state=state
            )
        )

    ####################################################################################################################
    #
    #  Execution Endpoints
    #
    ####################################################################################################################

    def create_execution(self, project, domain, name, execution_spec):
        """
        This will create an execution for the given execution spec.
        :param Text project:
        :param Text domain:
        :param Text name:
        :param flytekit.models.execution.ExecutionSpec execution_spec: This is the specification for the execution.
        :returns: The unique identifier for the execution.
        :rtype: flytekit.models.core.identifier.WorkflowExecutionIdentifier
        """
        return _identifier.WorkflowExecutionIdentifier.from_flyte_idl(
            super(SynchronousFlyteClient, self).create_execution(
                _execution_pb2.ExecutionCreateRequest(
                    project=project,
                    domain=domain,
                    name=name,
                    spec=execution_spec.to_flyte_idl()
                )
            ).id
        )

    def get_execution(self, id):
        """
        :param flytekit.common.core.identifier.WorkflowExecutionIdentifier id:
        :rtype: flytekit.models.execution.Execution
        """
        return _execution.Execution.from_flyte_idl(
            super(SynchronousFlyteClient, self).get_execution(
                _execution_pb2.WorkflowExecutionGetRequest(
                    id=id.to_flyte_idl()
                )
            )
        )

    def list_executions_paginated(
            self,
            project,
            domain,
            limit=100,
            token=None,
            filters=None,
            sort_by=None
    ):
        """
        This returns a page of executions in a given project and domain.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param Text project: Project in which to list executions.
        :param Text domain: Project in which to list executions.
        :param int limit: [Optional] The maximum number of entries to return.  Must be greater than 0.  The maximum
            page size is determined by the Flyte Admin Service configuration.  If limit is greater than the maximum
            page size, an exception will be raised.
        :param Text token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
            If you previously retrieved a page response with token="foo" and you want the next page,
            specify token="foo". Please see the notes for this function about the caveats of the paginated API.
        :param list[flytekit.models.filters.Filter] filters: [Optional] If specified, the filters will be applied to
            the query.  If the filter is not supported, an exception will be raised.
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :raises: TODO
        :rtype: (list[flytekit.models.execution.Execution], Text)
        """
        exec_list = super(SynchronousFlyteClient, self).list_executions_paginated(
            resource_list_request=_common_pb2.ResourceListRequest(
                id=_common_pb2.NamedEntityIdentifier(
                    project=project,
                    domain=domain
                ),
                limit=limit,
                token=token,
                filters=_filters.FilterList(filters or []).to_flyte_idl(),
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        return [_execution.Execution.from_flyte_idl(pb) for pb in exec_list.executions], _six.text_type(exec_list.token)

    def terminate_execution(self, id, cause):
        """
        :param flytekit.common.core.identifier.WorkflowExecutionIdentifier id:
        :param Text cause:
        """
        super(SynchronousFlyteClient, self).terminate_execution(
            _execution_pb2.ExecutionTerminateRequest(
                id=id.to_flyte_idl(),
                cause=cause
            )
        )

    ####################################################################################################################
    #
    #  Node Execution Endpoints
    #
    ####################################################################################################################

    def get_node_execution(self, node_execution_identifier):
        """
        :param flytekit.models.core.identifier.NodeExecutionIdentifier node_execution_identifier:
        :rtype: flytekit.models.node_execution.NodeExecution
        """
        return _node_execution.NodeExecution.from_flyte_idl(
            super(SynchronousFlyteClient, self).get_node_execution(
                _node_execution_pb2.NodeExecutionGetRequest(
                    id=node_execution_identifier.to_flyte_idl()
                )
            )
        )

    def list_node_executions(
            self,
            workflow_execution_identifier,
            limit=100,
            token=None,
            filters=None,
            sort_by=None
    ):
        """
        TODO: Comment
        :param flytekit.models.core.identifier.WorkflowExecutionIdentifier workflow_execution_identifier:
        :param int limit:
        :param Text token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
        If you previously retrieved a page response with token="foo" and you want the next page,
        specify token="foo".
        :param list[flytekit.models.filters.Filter] filters:
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :rtype: list[flytekit.models.node_execution.NodeExecution], Text
        """
        exec_list = super(SynchronousFlyteClient, self).list_node_executions_paginated(
            _node_execution_pb2.NodeExecutionListRequest(
                workflow_execution_id=workflow_execution_identifier.to_flyte_idl(),
                limit=limit,
                token=token,
                filters=_filters.FilterList(filters or []).to_flyte_idl(),
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        return [_node_execution.NodeExecution.from_flyte_idl(e) for e in exec_list.node_executions], \
            _six.text_type(exec_list.token)

    def list_node_executions_for_task_paginated(
            self,
            task_execution_identifier,
            limit=100,
            token=None,
            filters=None,
            sort_by=None
    ):
        """
        This returns nodes spawned by a specific task execution.  This is generally from things like dynamic tasks.
        :param flytekit.models.core.identifier.TaskExecutionIdentifier task_execution_identifier:
        :param int limit: Number to return per page
        :param Text token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
        If you previously retrieved a page response with token="foo" and you want the next page,
        specify token="foo".
        :param list[flytekit.models.filters.Filter] filters:
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :rtype: list[flytekit.models.node_execution.NodeExecution], Text
        """
        exec_list = self._stub.ListNodeExecutionsForTask(
            _node_execution_pb2.NodeExecutionForTaskListRequest(
                task_execution_id=task_execution_identifier.to_flyte_idl(),
                limit=limit,
                token=token,
                filters=_filters.FilterList(filters or []).to_flyte_idl(),
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        return [_node_execution.NodeExecution.from_flyte_idl(e) for e in exec_list.node_executions], \
            _six.text_type(exec_list.token)

    ####################################################################################################################
    #
    #  Task Execution Endpoints
    #
    ####################################################################################################################

    def get_task_execution(self, id):
        """
        :param flytekit.models.core.identifier.TaskExecutionIdentifier id:
        :rtype: flytekit.models.admin.task_execution.TaskExecution
        """
        return _task_execution.TaskExecution.from_flyte_idl(
            super(SynchronousFlyteClient, self).get_task_execution(
                _task_execution_pb2.TaskExecutionGetRequest(
                    id=id.to_flyte_idl()
                )
            )
        )

    def list_task_executions_paginated(self, node_execution_identifier, limit=100, token=None, filters=None,
                                       sort_by=None):
        """
        :param flytekit.models.core.identifier.NodeExecutionIdentifier node_execution_identifier:
        :param int limit:
        :param Text token: [Optional] If specified, this specifies where in the rows of results to skip before reading.
        If you previously retrieved a page response with token="foo" and you want the next page,
        specify token="foo".
        :param list[flytekit.models.filters.Filter] filters:
        :param flytekit.models.admin.common.Sort sort_by: [Optional] If provided, the results will be sorted.
        :rtype: (list[flytekit.models.admin.task_execution.TaskExecution], Text)
        """
        exec_list = super(SynchronousFlyteClient, self).list_task_executions_paginated(
            _task_execution_pb2.TaskExecutionListRequest(
                node_execution_id=node_execution_identifier.to_flyte_idl(),
                limit=limit,
                token=token,
                filters=_filters.FilterList(filters or []).to_flyte_idl(),
                sort_by=None if sort_by is None else sort_by.to_flyte_idl()
            )
        )
        return [_task_execution.TaskExecution.from_flyte_idl(e) for e in exec_list.task_executions], \
            _six.text_type(exec_list.token)

    ####################################################################################################################
    #
    #  Project Endpoints
    #
    ####################################################################################################################

    def register_project(self, project):
        """
        Registers a project.
        :param flytekit.models.project.Project project:
        :rtype: flyteidl.admin.project_pb2.ProjectRegisterResponse
        """
        super(SynchronousFlyteClient, self).register_project(
            _project_pb2.ProjectRegisterRequest(
                project=project.to_flyte_idl(),
            )
        )
