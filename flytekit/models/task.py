from __future__ import absolute_import

import json as _json

import six as _six
from flyteidl.admin import task_pb2 as _admin_task
from flyteidl.core import tasks_pb2 as _core_task, literals_pb2 as _literals_pb2, compiler_pb2 as _compiler
from flyteidl.plugins import spark_pb2 as _spark_task, sidecar_pb2 as _sidecar_task
from google.protobuf import json_format as _json_format, struct_pb2 as _struct

from flytekit.models import common as _common, literals as _literals, interface as _interface
from flytekit.models.core import identifier as _identifier


class Resources(_common.FlyteIdlEntity):

    class ResourceName(object):
        UNKNOWN = _core_task.Resources.UNKNOWN
        CPU = _core_task.Resources.CPU
        GPU = _core_task.Resources.GPU
        MEMORY = _core_task.Resources.MEMORY
        STORAGE = _core_task.Resources.STORAGE

    class ResourceEntry(_common.FlyteIdlEntity):

        def __init__(self, name, value):
            """
            :param int name: enum value from ResourceName
            :param Text value: a textual value describing the resource need.  Must be a valid k8s quantity.
            """
            self._name = name
            self._value = value

        @property
        def name(self):
            """
            enum value from ResourceName
            :rtype: int
            """
            return self._name

        @property
        def value(self):
            """
            A textual value describing the resource need.  Must be a valid k8s quantity.
            :rtype: Text
            """
            return self._value

        def to_flyte_idl(self):
            """
            :rtype: flyteidl.core.tasks_pb2.ResourceEntry
            """
            return _core_task.Resources.ResourceEntry(name=self.name, value=self.value)

        @classmethod
        def from_flyte_idl(cls, pb2_object):
            """
            :param flyteidl.core.tasks_pb2.Resources.ResourceEntry pb2_object:
            :rtype: Resources.ResourceEntry
            """
            return cls(name=pb2_object.name, value=pb2_object.value)

    def __init__(self, requests, limits):
        """
        :param list[Resources.ResourceEntry] requests: The desired resources for execution.  This is given on a best
            effort basis.
        :param list[Resources.ResourceEntry] limits: These are the limits required.  These are guaranteed to be
            satisfied.
        """
        self._requests = requests
        self._limits = limits

    @property
    def requests(self):
        """
        The desired resources for execution.  This is given on a best effort basis.
        :rtype: list[Resources.ResourceEntry]
        """
        return self._requests

    @property
    def limits(self):
        """
        These are the limits required.  These are guaranteed to be satisfied.
        :rtype: list[Resources.ResourceEntry]
        """
        return self._limits

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.core.tasks_pb2.Resources
        """
        return _core_task.Resources(
            requests=[r.to_flyte_idl() for r in self.requests],
            limits=[r.to_flyte_idl() for r in self.limits]
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.core.tasks_pb2.Resources.ResourceEntry pb2_object:
        :rtype: Resources
        """
        return cls(
            requests=[Resources.ResourceEntry.from_flyte_idl(r) for r in pb2_object.requests],
            limits=[Resources.ResourceEntry.from_flyte_idl(l) for l in pb2_object.limits]
        )


class RuntimeMetadata(_common.FlyteIdlEntity):

    class RuntimeType(object):
        OTHER = 0
        FLYTE_SDK = 1

    def __init__(self, type, version, flavor):
        """
        :param int type: Enum type from RuntimeMetadata.RuntimeType
        :param Text version: Version string for SDK version.  Can be used for metrics or managing breaking changes in
            Admin or Propeller
        :param Text flavor: Optional extra information about runtime environment (e.g. Python, GoLang, etc.)
        """
        self._type = type
        self._version = version
        self._flavor = flavor

    @property
    def type(self):
        """
        Enum type from RuntimeMetadata.RuntimeType
        :rtype: int
        """
        return self._type

    @property
    def version(self):
        """
        Version string for SDK version.  Can be used for metrics or managing breaking changes in Admin or Propeller
        :rtype: Text
        """
        return self._version

    @property
    def flavor(self):
        """
        Optional extra information about runtime environment (e.g. Python, GoLang, etc.)
        :rtype: Text
        """
        return self._flavor

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.core.tasks_pb2.RuntimeMetadata
        """
        return _core_task.RuntimeMetadata(
            type=self.type,
            version=self.version,
            flavor=self.flavor
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.core.tasks_pb2.RuntimeMetadata pb2_object:
        :rtype: RuntimeMetadata
        """
        return cls(
            type=pb2_object.type,
            version=pb2_object.version,
            flavor=pb2_object.flavor
        )


class TaskMetadata(_common.FlyteIdlEntity):

    def __init__(self, discoverable, runtime, timeout, retries, discovery_version, deprecated_error_message):
        """
        Information needed at runtime to determine behavior such as whether or not outputs are discoverable, timeouts,
        and retries.

        :param bool discoverable: Whether or not the outputs of this task should be cached for discovery.
        :param RuntimeMetadata runtime: Metadata describing the runtime environment for this task.
        :param datetime.timedelta timeout: The amount of time to wait before timing out.  This includes queuing and
            scheduler latency.
        :param flytekit.models.literals.RetryStrategy retries: Retry strategy for this task.  0 retries means only
            try once.
        :param Text discovery_version: This is the version used to create a logical version for data in the cache.
            This is only used when `discoverable` is true.  Data is considered discoverable if: the inputs to a given
            task are the same and the discovery_version is also the same.
        :param Text deprecated: This string can be used to mark the task as deprecated.  Consumers of the task will
            receive deprecation warnings.
        """
        self._discoverable = discoverable
        self._runtime = runtime
        self._timeout = timeout
        self._retries = retries
        self._discovery_version = discovery_version
        self._deprecated_error_message = deprecated_error_message

    @property
    def discoverable(self):
        """
        Whether or not the outputs of this task should be cached for discovery.
        :rtype: bool
        """
        return self._discoverable

    @property
    def runtime(self):
        """
        Metadata describing the runtime environment for this task.
        :rtype: RuntimeMetadata
        """
        return self._runtime

    @property
    def retries(self):
        """
        Retry strategy for this task.  0 retries means only try once.
        :rtype: flytekit.models.literals.RetryStrategy
        """
        return self._retries

    @property
    def timeout(self):
        """
        The amount of time to wait before timing out.  This includes queuing and scheduler latency.
        :rtype: datetime.timedelta
        """
        return self._timeout

    @property
    def discovery_version(self):
        """
        This is the version used to create a logical version for data in the cache.
        This is only used when `discoverable` is true.  Data is considered discoverable if: the inputs to a given
        task are the same and the discovery_version is also the same.
        :rtype: Text
        """
        return self._discovery_version

    @property
    def deprecated_error_message(self):
        """
        This string can be used to mark the task as deprecated.  Consumers of the task will receive deprecation
        warnings.
        :rtype: Text
        """
        return self._deprecated_error_message

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.admin.task_pb2.TaskMetadata
        """
        tm = _core_task.TaskMetadata(
            discoverable=self.discoverable,
            runtime=self.runtime.to_flyte_idl(),
            retries=self.retries.to_flyte_idl(),
            discovery_version=self.discovery_version,
            deprecated_error_message=self.deprecated_error_message
        )
        tm.timeout.FromTimedelta(self.timeout)
        return tm

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.core.task_pb2.TaskMetadata pb2_object:
        :rtype: TaskMetadata
        """
        return cls(
            discoverable=pb2_object.discoverable,
            runtime=RuntimeMetadata.from_flyte_idl(pb2_object.runtime),
            timeout=pb2_object.timeout.ToTimedelta(),
            retries=_literals.RetryStrategy.from_flyte_idl(pb2_object.retries),
            discovery_version=pb2_object.discovery_version,
            deprecated_error_message=pb2_object.deprecated_error_message
        )


class TaskTemplate(_common.FlyteIdlEntity):

    def __init__(self, id, type, metadata, interface, custom, container=None):
        """
        A task template represents the full set of information necessary to perform a unit of work in the Flyte system.
        It contains the metadata about what inputs and outputs are consumed or produced.  It also contains the metadata
        necessary for Flyte Propeller to do the appropriate work.

        :param flytekit.models.core.identifier.Identifier id: This is generated by the system and uniquely identifies
            the task.
        :param Text type: This is used to define additional extensions for use by Propeller or SDK.
        :param TaskMetadata metadata: This contains information needed at runtime to determine behavior such as
            whether or not outputs are discoverable, timeouts, and retries.
        :param flytekit.models.interface.TypedInterface interface: The interface definition for this task.
        :param dict[Text, T] custom: Dictionary that must be serializable to a protobuf Struct for custom task plugins.
        :param Container container: Provides the necessary entrypoint information for execution.  For instance,
            a Container might be specified with the necessary command line arguments.
        """
        self._id = id
        self._type = type
        self._metadata = metadata
        self._interface = interface
        self._custom = custom
        self._container = container

    @property
    def id(self):
        """
        This is generated by the system and uniquely identifies the task.
        :rtype: flytekit.models.core.identifier.Identifier
        """
        return self._id

    @property
    def type(self):
        """
        This is used to identify additional extensions for use by Propeller or SDK.
        :rtype: Text
        """
        return self._type

    @property
    def metadata(self):
        """
        This contains information needed at runtime to determine behavior such as whether or not outputs are
        discoverable, timeouts, and retries.
        :rtype: TaskMetadata
        """
        return self._metadata

    @property
    def interface(self):
        """
        The interface definition for this task.
        :rtype: flytekit.common.interface.TypedInterface
        """
        return self._interface

    @property
    def custom(self):
        """
        Arbitrary dictionary containing metadata for custom plugins.
        :rtype: dict[Text, T]
        """
        return self._custom

    @property
    def container(self):
        """
        If not None, the target of execution should be a container.
        :rtype: Container
        """
        return self._container

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.core.tasks_pb2.TaskTemplate
        """
        return _core_task.TaskTemplate(
            id=self.id.to_flyte_idl(),
            type=self.type,
            metadata=self.metadata.to_flyte_idl(),
            interface=self.interface.to_flyte_idl(),
            custom=_json_format.Parse(_json.dumps(self.custom), _struct.Struct()) if self.custom else None,
            container=self.container.to_flyte_idl() if self.container else None
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.core.tasks_pb2.TaskTemplate pb2_object:
        :rtype: TaskTemplate
        """
        return cls(
            id=_identifier.Identifier.from_flyte_idl(pb2_object.id),
            type=pb2_object.type,
            metadata=TaskMetadata.from_flyte_idl(pb2_object.metadata),
            interface=_interface.TypedInterface.from_flyte_idl(pb2_object.interface),
            custom=_json_format.MessageToDict(pb2_object.custom) if pb2_object else None,
            container=Container.from_flyte_idl(pb2_object.container) if pb2_object.HasField("container") else None
        )


class TaskSpec(_common.FlyteIdlEntity):

    def __init__(self, template):
        """
        :param TaskTemplate template:
        """
        self._template = template

    @property
    def template(self):
        """
        :rtype: TaskTemplate
        """
        return self._template

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.admin.tasks_pb2.TaskSpec
        """
        return _admin_task.TaskSpec(
            template=self.template.to_flyte_idl()
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.admin.tasks_pb2.TaskSpec pb2_object:
        :rtype: TaskSpec
        """
        return cls(TaskTemplate.from_flyte_idl(pb2_object.template))


class Task(_common.FlyteIdlEntity):

    def __init__(self, id, closure):
        """
        :param flytekit.models.core.identifier.Identifier id: The (project, domain, name) identifier for this task.
        :param TaskClosure closure: The closure for the underlying workload.
        """
        self._id = id
        self._closure = closure

    @property
    def id(self):
        """
        The (project, domain, name, version) identifier for this task.
        :rtype: flytekit.models.core.identifier.Identifier
        """
        return self._id

    @property
    def closure(self):
        """
        The closure for the underlying workload.
        :rtype: TaskClosure
        """
        return self._closure

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.admin.task_pb2.Task
        """
        return _admin_task.Task(
            closure=self.closure.to_flyte_idl(),
            id=self.id.to_flyte_idl(),
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.admin.task_pb2.Task pb2_object:
        :rtype: TaskDefinition
        """
        return cls(
            closure=TaskClosure.from_flyte_idl(pb2_object.closure),
            id=_identifier.Identifier.from_flyte_idl(pb2_object.id)
        )


class TaskClosure(_common.FlyteIdlEntity):

    def __init__(self, compiled_task):
        """
        :param CompiledTask compiled_task:
        """
        self._compiled_task = compiled_task

    @property
    def compiled_task(self):
        """
        :rtype: CompiledTask
        """
        return self._compiled_task

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.admin.task_pb2.TaskClosure
        """
        return _admin_task.TaskClosure(
            compiled_task=self.compiled_task.to_flyte_idl()
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.admin.task_pb2.TaskClosure pb2_object:
        :rtype: TaskClosure
        """
        return cls(
            compiled_task=CompiledTask.from_flyte_idl(pb2_object.compiled_task)
        )


class CompiledTask(_common.FlyteIdlEntity):

    def __init__(self, template):
        """
        :param TaskTemplate template:
        """
        self._template = template

    @property
    def template(self):
        """
        :rtype: TaskTemplate
        """
        return self._template

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.core.compiler_pb2.CompiledTask
        """
        return _compiler.CompiledTask(
            template=self.template.to_flyte_idl()
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.core.compiler_pb2.CompiledTask pb2_object:
        :rtype: CompiledTask
        """
        return cls(
            template=TaskTemplate.from_flyte_idl(pb2_object.template)
        )


class SparkJob(_common.FlyteIdlEntity):

    def __init__(self, application_file, spark_conf, hadoop_conf, executor_path):
        """
        This defines a SparkJob target.  It will execute the appropriate SparkJob.

        :param application_file: The main application file to execute.
        :param dict[Text, Text] spark_conf: A definition of key-value pairs for spark config for the job.
        :param dict[Text, Text] hadoop_conf: A definition of key-value pairs for hadoop config for the job.
        """
        self._application_file = application_file
        self._executor_path = executor_path
        self._spark_conf = spark_conf
        self._hadoop_conf = hadoop_conf

    @property
    def application_file(self):
        """
        The main application file to execute
        :rtype: Text
        """
        return self._application_file

    @property
    def executor_path(self):
        """
        The python executable to use
        :rtype: Text
        """
        return self._executor_path

    @property
    def spark_conf(self):
        """
       A definition of key-value pairs for spark config for the job.
        :rtype: dict[Text, Text]
        """
        return self._spark_conf

    @property
    def hadoop_conf(self):
        """
         A definition of key-value pairs for hadoop config for the job.
        :rtype: dict[Text, Text]
        """
        return self._hadoop_conf

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.plugins.spark_pb2.SparkJob
        """
        return _spark_task.SparkJob(
            mainApplicationFile=self.application_file,
            executorPath=self.executor_path,
            sparkConf=self.spark_conf,
            hadoopConf=self.hadoop_conf,
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.plugins.spark_pb2.SparkJob pb2_object:
        :rtype: SparkJob
        """
        return cls(
            spark_conf=pb2_object.sparkConf,
            application_file=pb2_object.mainApplicationFile,
            hadoop_conf=pb2_object.hadoopConf,
            executor_path=pb2_object.executorPath,
        )


class Container(_common.FlyteIdlEntity):

    def __init__(self, image, command, args, resources, env, config):
        """
        This defines a container target.  It will execute the appropriate command line on the appropriate image with
        the given configurations.

        :param Text image: The fully-qualified identifier for the image.
        :param list[Text] command: A list of 'words' for the command.  i.e. ['aws', 's3', 'ls']
        :param list[Text] args: A list of arguments for the command.  i.e. ['s3://some/path', '/tmp/local/path']
        :param Resources resources: A definition of requisite compute resources.
        :param dict[Text, Text] env: A definition of key-value pairs for environment variables.
        :param dict[Text, Text] config: A definition of configuration key-value pairs.
        """
        self._image = image
        self._command = command
        self._args = args
        self._resources = resources
        self._env = env
        self._config = config

    @property
    def image(self):
        """
        The fully-qualified identifier for the image.
        :rtype: Text
        """
        return self._image

    @property
    def command(self):
        """
        A list of 'words' for the command.  i.e. ['aws', 's3', 'ls']
        :rtype: list[Text]
        """
        return self._command

    @property
    def args(self):
        """
         A list of arguments for the command.  i.e. ['s3://some/path', '/tmp/local/path']
        :rtype: list[Text]
        """
        return self._args

    @property
    def resources(self):
        """
        A definition of requisite compute resources.
        :rtype: Resources
        """
        return self._resources

    @property
    def env(self):
        """
        A definition of key-value pairs for environment variables.  Currently, only str->str is
            supported.
        :rtype: dict[Text, Text]
        """
        return self._env

    @property
    def config(self):
        """
        A definition of key-value pairs for configuration.  Currently, only str->str is
            supported.
        :rtype: dict[Text, Text]
        """
        return self._config

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.core.tasks_pb2.Container
        """
        return _core_task.Container(
            image=self.image,
            command=self.command,
            args=self.args,
            resources=self.resources.to_flyte_idl(),
            env=[_literals_pb2.KeyValuePair(key=k, value=v) for k, v in _six.iteritems(self.env)],
            config=[_literals_pb2.KeyValuePair(key=k, value=v) for k, v in _six.iteritems(self.config)]
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.admin.task_pb2.Task pb2_object:
        :rtype: Container
        """
        return cls(
            image=pb2_object.image,
            command=pb2_object.command,
            args=pb2_object.args,
            resources=Resources.from_flyte_idl(pb2_object.resources),
            env={kv.key: kv.value for kv in pb2_object.env},
            config={kv.key: kv.value for kv in pb2_object.config}
        )


class SidecarJob(_common.FlyteIdlEntity):

    def __init__(self, pod_spec, primary_container_name):
        """
        A sidecar job represents the full kubernetes pod spec and related metadata required for executing a sidecar
        task.

        :param pod_spec: k8s.io.api.core.v1.PodSpec
        :param primary_container_name: Text
        """
        self._pod_spec = pod_spec
        self._primary_container_name = primary_container_name

    @property
    def pod_spec(self):
        """
        :rtype: k8s.io.api.core.v1.PodSpec
        """
        return self._pod_spec

    @property
    def primary_container_name(self):
        """
        :rtype: Text
        """
        return self._primary_container_name

    def to_flyte_idl(self):
        """
        :rtype: flyteidl.core.tasks_pb2.SidecarJob
        """
        return _sidecar_task.SidecarJob(
            pod_spec=self.pod_spec,
            primary_container_name=self.primary_container_name
        )

    @classmethod
    def from_flyte_idl(cls, pb2_object):
        """
        :param flyteidl.admin.task_pb2.Task pb2_object:
        :rtype: Container
        """
        return cls(
            pod_spec=pb2_object.pod_spec,
            primary_container_name=pb2_object.primary_container_name,
        )
