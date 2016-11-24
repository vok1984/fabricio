import dummy_threading
import functools
import json
import re
import sys

import dpath
import six

from cached_property import cached_property
from fabric import api as fab, colors
from frozendict import frozendict

import fabricio

from fabricio import utils

from .base import BaseService, Option, Attribute
from .container import Container


class ServiceNotFoundError(RuntimeError):
    pass


class RemovableOption(Option):

    get_values = staticmethod(dpath.util.values)

    path = None

    value_type = six.text_type

    def __init__(self, func=None, path=None, **kwargs):
        super(RemovableOption, self).__init__(func=func, **kwargs)
        self.path = path or self.path

    def get_current_values(self, service):
        return self.get_values(service.info, self.path)

    def get_remove_values(self, service, attr):
        current_values = self.get_current_values(service)
        if not current_values:
            return None
        new_values = self.get_add_values(service, attr)
        return set(current_values).difference(new_values)

    def get_add_values(self, service, attr):
        values = getattr(service, attr)
        if values is None:
            return []
        if isinstance(values, six.string_types):
            values = [values]
        return map(self.value_type, values)


class Label(RemovableOption):

    get_values = staticmethod(dpath.util.get)

    class value_type(utils.Item):

        def get_comparison_value(self):
            # fetch label key
            return self.split('=', 1)[0]

    def get_current_values(self, service):
        try:
            return super(Label, self).get_current_values(service)
        except KeyError:
            return []


class Port(RemovableOption):

    path = '/Spec/EndpointSpec/Ports/*/TargetPort'

    class value_type(utils.Item):

        def get_comparison_value(self):
            # fetch target port
            return self.rsplit('/', 1)[0].rsplit(':', 1)[-1]


class Mount(RemovableOption):

    path = '/Spec/TaskTemplate/ContainerSpec/Mounts/*/Target'

    class value_type(utils.Item):

        comparison_value_re = re.compile(
            'destination=(?P<quote>[\'"]?)(?P<dst>.*?)(?P=quote)(?:,|$)',
            flags=re.UNICODE,
        )

        def get_comparison_value(self):
            # fetch target path
            match = self.comparison_value_re.search(self)
            return match and match.group('dst')


class Service(BaseService):

    sentinel = None

    # allow all tasks to be executed in parallel
    lock = dummy_threading.RLock()

    @property
    def image(self):
        return self.sentinel.image

    @Attribute
    def command(self):
        return self.sentinel.command

    args = Attribute()

    labels = Label(name='label', path='/Spec/Labels')

    container_labels = Label(
        name='container-label',
        path='/Spec/TaskTemplate/ContainerSpec/Labels',
    )

    constraints = RemovableOption(
        name='constraint',
        path='/Spec/TaskTemplate/Placement/Constraints/*',
    )

    replicas = Option(default=1)

    mounts = Mount(name='mount')

    network = Option()

    restart_condition = Option(name='restart-condition')

    @Option(name='stop-grace-period')
    def stop_timeout(self):
        return self.sentinel and self.sentinel.stop_timeout

    @RemovableOption(path='/Spec/TaskTemplate/ContainerSpec/Env/*')
    def env(self):
        return self.sentinel and self.sentinel.env

    @Port(name='publish')
    def ports(self):
        return self.sentinel.ports

    @Option
    def user(self):
        return self.sentinel and self.sentinel.user

    def __init__(self, image=None, sentinel=None, options=None, **attrs):
        super(Service, self).__init__(options=options, **attrs)
        sentinel = sentinel or self.sentinel
        if sentinel:
            sentinel_name = sentinel.name or self.name
            sentinel = sentinel.fork(name=sentinel_name, image=image)
        else:
            sentinel = Container(
                name=self.name,
                image=image,
                stop_timeout=self.stop_timeout,
                options=dict(
                    env=self.env,
                    user=self.user,
                ),
            )
        self.sentinel = sentinel

    def fork(self, image=None, sentinel=None, options=None, **attrs):
        image = image or self.image
        sentinel = sentinel or self.sentinel
        return super(Service, self).fork(
            image=image,
            sentinel=sentinel,
            options=options,
            **attrs
        )

    @cached_property
    def _update_options(self):
        options = {}
        for cls in type(self).__mro__[::-1]:
            for attr, option in vars(cls).items():
                if isinstance(option, Option):
                    def get_values(service, attr=attr):
                        return getattr(service, attr)
                    name = option.name or attr
                    if isinstance(option, RemovableOption):
                        options[name + '-rm'] = functools.partial(
                            option.get_remove_values,
                            attr=attr,
                        )
                        options[name + '-add'] = get_values
                    else:
                        options[name] = get_values
        return options

    @property
    def update_options(self):
        with utils.patch(self, 'info', self.info, force_delete=True):
            return frozendict(
                [
                    (option, callback(self))
                    for option, callback in self._update_options.items()
                ],
                args=self.args,
                **self._additional_options
            )

    def _update(self, update_options):
        fabricio.run('docker service update {options} {service}'.format(
            options=update_options,
            service=self,
        ))

    def _create(self):
        pass  # TODO
        # TODO command += args

    def update(self, tag=None, registry=None, force=False):
        if not self.is_manager():
            return False

        image_digest = self.image[registry:tag].digest

        try:
            update_options = str(utils.Options(
                self.update_options,
                image=image_digest,
            ))
            label = '__service_options={0}'.format(json.dumps(update_options))
            sentinel_labels = self.sentinel.labels
            try:
                sentinel_labels.append(label)
            except AttributeError:
                if sentinel_labels:
                    self.sentinel.labels = [sentinel_labels, label]
                else:
                    self.sentinel.labels = label
        except ServiceNotFoundError:
            update_options = None

        sentinel_updated = self.sentinel.update(
            tag=tag,
            registry=registry,
            force=force,
            run=False,
        )

        if not sentinel_updated:
            return False

        if self.is_leader():
            if update_options is None:
                self._create()  # TODO create_options
            else:
                self._update(update_options)

        return True

    def revert(self):
        pass  # TODO finish implementation

    def pull_image(self, tag=None, registry=None):
        try:
            self.sentinel.pull_image(tag=tag, registry=registry)
        except RuntimeError as error:
            if self.is_manager():
                # inability to pull image is critical only for Swarm managers
                # because they have to keep up to date their sentinel
                # containers
                raise
            fabricio.log(
                "WARNING: {host} could not pull image: {error}".format(
                    host=fab.env.host,
                    error=error,
                ),
                color=colors.red,
                output=sys.stderr,
            )

    def migrate(self, tag=None, registry=None):
        if self.is_leader():
            self.sentinel.migrate(tag=tag, registry=registry)

    def migrate_back(self):
        if self.is_leader():
            self.sentinel.migrate_back()

    def backup(self):
        if self.is_leader():
            self.sentinel.backup()

    def restore(self, backup_name=None):
        if self.is_leader():
            self.sentinel.restore(backup_name=backup_name)

    @utils.default_property
    def info(self):
        command = 'docker service inspect {service}'
        info = fabricio.run(
            command.format(service=self),
            abort_exception=ServiceNotFoundError,
        )
        return json.loads(info)[0]

    @property
    def _leader_status(self):
        return fabricio.run(
            "docker node inspect --format '{{.ManagerStatus.Leader}}' self",
            ignore_errors=True,
            use_cache=True,
        )

    def is_manager(self):
        # 'docker node inspect self' works only on manager nodes
        return self._leader_status.succeeded

    def is_leader(self):
        return self._leader_status == 'true'
