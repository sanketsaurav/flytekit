from __future__ import absolute_import

import six as _six

from flyteidl.core import tasks_pb2 as _core_task

from flytekit.common.exceptions import user as _user_exceptions
from flytekit.common.tasks import sdk_runnable as _sdk_runnable
from flytekit.common import sdk_bases as _sdk_bases

from flytekit.models import task as _task_models
from google.protobuf.json_format import MessageToDict as _MessageToDict

import k8s.io.api.core.v1.generated_pb2 as _k8s_pb2
import k8s.io.apimachinery.pkg.api.resource.generated_pb2 as _resource_pb2


class SdkSidecarTask(_six.with_metaclass(_sdk_bases.ExtendedSdkType, _sdk_runnable.SdkRunnableTask)):

    """
    This class includes the additional logic for building a task that executes as a Sidecar Job.

    """

    def __init__(self,
                 task_function,
                 task_type,
                 discovery_version,
                 retries,
                 deprecated,
                 storage_request,
                 cpu_request,
                 gpu_request,
                 memory_request,
                 storage_limit,
                 cpu_limit,
                 gpu_limit,
                 memory_limit,
                 discoverable,
                 timeout,
                 environment,
                 pod_spec=None,
                 primary_container_name=None):
        """
        :param _sdk_runnable.SdkRunnableTask sdk_runnable_task:
        :param generated_pb2.PodSpec pod_spec:
        :param Text primary_container_name:
        :raises: flytekit.common.exceptions.user.FlyteValidationException
        """
        if not pod_spec:
            raise _user_exceptions.FlyteValidationException("A pod spec cannot be undefined")
        if not primary_container_name:
            raise _user_exceptions.FlyteValidationException("A primary container name cannot be undefined")

        super(SdkSidecarTask, self).__init__(
            task_function,
            task_type,
            discovery_version,
            retries,
            deprecated,
            storage_request,
            cpu_request,
            gpu_request,
            memory_request,
            storage_limit,
            cpu_limit,
            gpu_limit,
            memory_limit,
            discoverable,
            timeout,
            environment,
            custom=None,
        )

        self.reconcile_partial_pod_spec_and_task(pod_spec, primary_container_name)

    def reconcile_partial_pod_spec_and_task(self,
                                            pod_spec,
                                            primary_container_name):
        """
        Assigns the custom field as a the reconciled primary container and pod spec defintion.
        :param _sdk_runnable.SdkRunnableTask sdk_runnable_task:
        :param generated_pb2.PodSpec pod_spec:
        :param Text primary_container_name:
        :rtype: SdkSidecarTask
        """

        # First, insert a placeholder primary container if it is not defined in the pod spec.
        containers = pod_spec.containers
        primary_exists = False
        for container in containers:
            if container.name == primary_container_name:
                primary_exists = True
                break
        if not primary_exists:
            containers.extend([_k8s_pb2.Container(name=primary_container_name)])

        final_containers = []
        for container in containers:
            # In the case of the primary container, we overwrite specific container attributes with the default values
            # used in an SDK runnable task.
            if container.name == primary_container_name:
                container.image = self._container.image
                # clear existing commands
                del container.command[:]
                container.command.extend(self._container.command)
                # also clear existing args
                del container.args[:]
                container.args.extend(self._container.args)

                resource_requirements = _k8s_pb2.ResourceRequirements()
                for resource in self._container.resources.limits:
                    resource_requirements.limits[
                        _core_task.Resources.ResourceName.Name(resource.name).lower()].CopyFrom(
                        _resource_pb2.Quantity(string=resource.value))
                for resource in self._container.resources.requests:
                    resource_requirements.requests[
                        _core_task.Resources.ResourceName.Name(resource.name).lower()].CopyFrom(
                        _resource_pb2.Quantity(string=resource.value))
                if resource_requirements.ByteSize():
                    # Important! Only copy over resource requirements if they are non-empty.
                    container.resources.CopyFrom(resource_requirements)

                del container.env[:]
                container.env.extend(
                    [_k8s_pb2.EnvVar(name=key, value=val) for key, val in
                     _six.iteritems(self._container.env)])

            final_containers.append(container)

        del pod_spec.containers[:]
        pod_spec.containers.extend(final_containers)

        sidecar_job_plugin = _task_models.SidecarJob(
            pod_spec=pod_spec,
            primary_container_name=primary_container_name,
        ).to_flyte_idl()

        self.assign_custom_and_return(_MessageToDict(sidecar_job_plugin))
