from __future__ import absolute_import
from grpc import insecure_channel as _insecure_channel, secure_channel as _secure_channel, RpcError as _RpcError, \
    StatusCode as _GrpcStatusCode, ssl_channel_credentials as _ssl_channel_credentials
from flyteidl.service import admin_pb2_grpc as _admin_service
from flytekit.common.exceptions import user as _user_exceptions
import six as _six


def _handle_rpc_error(fn):
    def handler(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except _RpcError as e:
            if e.code() == _GrpcStatusCode.ALREADY_EXISTS:
                raise _user_exceptions.FlyteEntityAlreadyExistsException(_six.text_type(e))
            else:
                raise
    return handler


class RawSynchronousFlyteClient(object):
    """
    This is a thin synchronous wrapper around the auto-generated GRPC stubs for communicating with the admin service.

    This client should be usable regardless of environment in which this is used. In other words, configurations should
    be explicit as opposed to inferred from the environment or a configuration file.
    """

    def __init__(self, url, insecure=False, credentials=None, options=None):
        """
        Initializes a gRPC channel to the given Flyte Admin service.

        :param Text url: The URL (including port if necessary) to connect to the appropriate Flyte Admin Service.
        :param bool insecure: [Optional] Whether to use an insecure connection, default False
        :param Text credentials: [Optional] If provided, a secure channel will be opened with the Flyte Admin Service.
        :param dict[Text, Text] options: [Optional] A dict of key-value string pairs for configuring the gRPC core
            runtime.
        """
        self._channel = None

        # TODO: Revert all the for loops below
        if insecure:
            self._channel = _insecure_channel(url, options=list((options or {}).items()))
        else:
            self._channel = _secure_channel(
                url,
                credentials or _ssl_channel_credentials(),
                options=list((options or {}).items())
            )
        self._stub = _admin_service.AdminServiceStub(self._channel)

    ####################################################################################################################
    #
    #  Task Endpoints
    #
    ####################################################################################################################

    @_handle_rpc_error
    def create_task(self, task_create_request):
        """
        This will create a task definition in the Admin database. Once successful, the task object can be
        retrieved via the client or viewed via the UI or command-line interfaces.

        .. note ::

            Overwrites are not supported so any request for a given project, domain, name, and version that exists in
            the database must match the existing definition exactly. This also means that as long as the request
            remains identical, calling this method multiple times will result in success.

        :param: flyteidl.admin.task_pb2.TaskCreateRequest task_create_request: The request protobuf object.
        :rtype: flyteidl.admin.task_pb2.TaskCreateResponse
        :raises flytekit.common.exceptions.user.FlyteEntityAlreadyExistsException: If an identical version of the task
            is found, this exception is raised.  The client might choose to ignore this exception because the identical
            task is already registered.
        :raises grpc.RpcError:
        """
        return self._stub.CreateTask(task_create_request)

    @_handle_rpc_error
    def list_task_ids_paginated(self, identifier_list_request):
        """
        This returns a page of identifiers for the tasks for a given project and domain. Filters can also be
        specified.

        .. note ::

            The name field in the TaskListRequest is ignored.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param: flyteidl.admin.common_pb2.NamedEntityIdentifierListRequest identifier_list_request:
        :rtype: flyteidl.admin.common_pb2.NamedEntityIdentifierList
        :raises: TODO
        """
        return self._stub.ListTaskIds(identifier_list_request)

    @_handle_rpc_error
    def list_tasks_paginated(self, resource_list_request):
        """
        This returns a page of task metadata for tasks in a given project and domain.  Optionally,
        specifying a name will limit the results to only tasks with that name in the given project and domain.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param: flyteidl.admin.common_pb2.ResourceListRequest resource_list_request:
        :rtype: flyteidl.admin.task_pb2.TaskList
        :raises: TODO
        """
        return self._stub.ListTasks(resource_list_request)

    @_handle_rpc_error
    def get_task(self, get_object_request):
        """
        This returns a single task for a given identifier.

        :param: flyteidl.admin.common_pb2.ObjectGetRequest get_object_request:
        :rtype: flyteidl.admin.task_pb2.Task
        :raises: TODO
        """
        return self._stub.GetTask(get_object_request)

    ####################################################################################################################
    #
    #  Workflow Endpoints
    #
    ####################################################################################################################

    @_handle_rpc_error
    def create_workflow(self, workflow_create_request):
        """
        This will create a workflow definition in the Admin database.  Once successful, the workflow object can be
        retrieved via the client or viewed via the UI or command-line interfaces.

        .. note ::

            Overwrites are not supported so any request for a given project, domain, name, and version that exists in
            the database must match the existing definition exactly.  This also means that as long as the request
            remains identical, calling this method multiple times will result in success.

        :param: flyteidl.admin.workflow_pb2.WorkflowCreateRequest workflow_create_request:
        :rtype: flyteidl.admin.workflow_pb2.WorkflowCreateResponse
        :raises flytekit.common.exceptions.user.FlyteEntityAlreadyExistsException: If an identical version of the
            workflow is found, this exception is raised.  The client might choose to ignore this exception because the
            identical workflow is already registered.
        :raises grpc.RpcError:
        """
        return self._stub.CreateWorkflow(workflow_create_request)

    @_handle_rpc_error
    def list_workflow_ids_paginated(self, identifier_list_request):
        """
        This returns a page of identifiers for the workflows for a given project and domain. Filters can also be
        specified.

        .. note ::

            The name field in the WorkflowListRequest is ignored.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param: flyteidl.admin.common_pb2.NamedEntityIdentifierListRequest identifier_list_request:
        :rtype: flyteidl.admin.common_pb2.NamedEntityIdentifierList
        :raises: TODO
        """
        return self._stub.ListWorkflowIds(identifier_list_request)

    @_handle_rpc_error
    def list_workflows_paginated(self, resource_list_request):
        """
        This returns a page of workflow meta-information for workflows in a given project and domain.  Optionally,
        specifying a name will limit the results to only workflows with that name in the given project and domain.

        .. note ::

            This is a paginated API.  Use the token field in the request to specify a page offset token.
            The user of the API is responsible for providing this token.

        .. note ::

            If entries are added to the database between requests for different pages, it is possible to receive
            entries on the second page that also appeared on the first.

        :param: flyteidl.admin.common_pb2.ResourceListRequest resource_list_request:
        :rtype: flyteidl.admin.workflow_pb2.WorkflowList
        :raises: TODO
        """
        return self._stub.ListWorkflows(resource_list_request)

    @_handle_rpc_error
    def get_workflow(self, get_object_request):
        """
        This returns a single workflow for a given identifier.

        :param: flyteidl.admin.common_pb2.ObjectGetRequest get_object_request:
        :rtype: flyteidl.admin.workflow_pb2.Workflow
        :raises: TODO
        """
        return self._stub.GetWorkflow(get_object_request)

    ####################################################################################################################
    #
    #  Launch Plan Endpoints
    #
    ####################################################################################################################

    @_handle_rpc_error
    def create_launch_plan(self, launch_plan_create_request):
        """
        This will create a launch plan definition in the Admin database.  Once successful, the launch plan object can be
        retrieved via the client or viewed via the UI or command-line interfaces.

        .. note ::

            Overwrites are not supported so any request for a given project, domain, name, and version that exists in
            the database must match the existing definition exactly.  This also means that as long as the request
            remains identical, calling this method multiple times will result in success.

        :param: flyteidl.admin.launch_plan_pb2.LaunchPlanCreateRequest launch_plan_create_request:  The request
            protobuf object
        :rtype: flyteidl.admin.launch_plan_pb2.LaunchPlanCreateResponse
        :raises flytekit.common.exceptions.user.FlyteEntityAlreadyExistsException: If an identical version of the
            launch plan is found, this exception is raised.  The client might choose to ignore this exception because
            the identical launch plan is already registered.
        :raises grpc.RpcError:
        """
        return self._stub.CreateLaunchPlan(launch_plan_create_request)

    # TODO: List endpoints when they come in

    @_handle_rpc_error
    def get_launch_plan(self, object_get_request):
        """
        Retrieves a launch plan entity.

        :param flyteidl.admin.common_pb2.ObjectGetRequest object_get_request:
        :rtype: flyteidl.admin.launch_plan_pb2.LaunchPlan
        """
        return self._stub.GetLaunchPlan(object_get_request)

    @_handle_rpc_error
    def update_launch_plan(self, update_request):
        """
        Allows updates to a launch plan at a given identifier.  Currently, a launch plan may only have it's state
        switched between ACTIVE and INACTIVE.

        :param flyteidl.admin.launch_plan_pb2.LaunchPlanUpdateRequest update_request:
        :rtype: flyteidl.admin.launch_plan_pb2.LaunchPlanUpdateResponse
        """
        return self._stub.UpdateLaunchPlan(update_request)

    @_handle_rpc_error
    def list_launch_plan_ids_paginated(self, identifier_list_request):
        """
        Lists launch plan named identifiers for a given project and domain.

        :param: flyteidl.admin.common_pb2.NamedEntityIdentifierListRequest identifier_list_request:
        :rtype: flyteidl.admin.common_pb2.NamedEntityIdentifierList
        """
        return self._stub.ListLaunchPlanIds(identifier_list_request)

    @_handle_rpc_error
    def list_launch_plans_paginated(self, resource_list_request):
        """
        Lists Launch Plans for a given Identifer (project, domain, name)

        :param: flyteidl.admin.common_pb2.ResourceListRequest resource_list_request:
        :rtype: flyteidl.admin.launch_plan_pb2.LaunchPlanList
        """
        return self._stub.ListLaunchPlans(resource_list_request)

    ####################################################################################################################
    #
    #  Workflow Execution Endpoints
    #
    ####################################################################################################################

    @_handle_rpc_error
    def create_execution(self, create_execution_request):
        """
        This will create an execution for the given execution spec.
        :param flyteidl.admin.execution_pb2.ExecutionCreateRequest create_execution_request:
        :rtype: flyteidl.admin.execution_pb2.ExecutionCreateResponse
        """
        return self._stub.CreateExecution(create_execution_request)

    @_handle_rpc_error
    def get_execution(self, get_object_request):
        """
        Returns an execution of a workflow entity.

        :param flyteidl.admin.execution_pb2.WorkflowExecutionGetRequest get_object_request:
        :rtype: flyteidl.admin.execution_pb2.Execution
        """
        return self._stub.GetExecution(get_object_request)

    @_handle_rpc_error
    def list_executions_paginated(self, resource_list_request):
        """
        Lists the executions for a given identifier.

        :param flyteidl.admin.common_pb2.ResourceListRequest resource_list_request:
        :rtype: flyteidl.admin.execution_pb2.ExecutionList
        """
        return self._stub.ListExecutions(resource_list_request)

    @_handle_rpc_error
    def terminate_execution(self, terminate_execution_request):
        """
        :param flyteidl.admin.execution_pb2.TerminateExecutionRequest terminate_execution_request:
        :rtype: flyteidl.admin.execution_pb2.TerminateExecutionResponse
        """
        return self._stub.TerminateExecution(terminate_execution_request)

    ####################################################################################################################
    #
    #  Node Execution Endpoints
    #
    ####################################################################################################################

    def get_node_execution(self, node_execution_request):
        """
        :param flyteidl.admin.node_execution_pb2.NodeExecutionGetRequest node_execution_request:
        :rtype: flyteidl.admin.node_execution_pb2.NodeExecution
        """
        return self._stub.GetNodeExecution(node_execution_request)

    def list_node_executions_paginated(self, node_execution_list_request):
        """
        :param flyteidl.admin.node_execution_pb2.NodeExecutionListRequest node_execution_list_request:
        :rtype: flyteidl.admin.node_execution_pb2.NodeExecutionList
        """
        return self._stub.ListNodeExecutions(node_execution_list_request)

    def list_node_executions_for_task_paginated(self, node_execution_for_task_list_request):
        """
        :param flyteidl.admin.node_execution_pb2.NodeExecutionListRequest node_execution_for_task_list_request:
        :rtype: flyteidl.admin.node_execution_pb2.NodeExecutionList
        """
        return self._stub.ListNodeExecutionsForTask(node_execution_for_task_list_request)

    ####################################################################################################################
    #
    #  Task Execution Endpoints
    #
    ####################################################################################################################

    def get_task_execution(self, task_execution_request):
        """
        :param flyteidl.admin.task_execution_pb2.TaskExecutionGetRequest task_execution_request:
        :rtype: flyteidl.admin.task_execution_pb2.TaskExecution
        """
        return self._stub.GetTaskExecution(task_execution_request)

    def list_task_executions_paginated(self, task_execution_list_request):
        """
        :param flyteidl.admin.task_execution_pb2.TaskExecutionListRequest task_execution_list_request:
        :rtype: flyteidl.admin.task_execution_pb2.TaskExecutionList
        """
        return self._stub.ListTaskExecutions(task_execution_list_request)

    ####################################################################################################################
    #
    #  Project Endpoints
    #
    ####################################################################################################################

    @_handle_rpc_error
    def list_projects(self, project_list_request):
        """
        This will return a list of the projects registered with the Flyte Admin Service
        :param flyteidl.admin.project_pb2.ProjectListRequest project_list_request:
        :rtype: flyteidl.admin.project_pb2.Projects
        """
        return self._stub.ListProjects(project_list_request)

    @_handle_rpc_error
    def register_project(self, project_register_request):
        """
        Registers a project along with a set of domains.
        :param flyteidl.admin.project_pb2.ProjectRegisterRequest project_register_request:
        :rtype: flyteidl.admin.project_pb2.ProjectRegisterResponse
        """
        return self._stub.RegisterProject(project_register_request)

    ####################################################################################################################
    #
    #  Event Endpoints
    #
    ####################################################################################################################

    # TODO: (P2) Implement the event endpoints in case there becomes a use-case for third-parties to submit events
    # through the client in Python.
