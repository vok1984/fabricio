import dummy_threading
import json
import sys

import six

from cached_property import cached_property
from fabric import api as fab, colors
from frozendict import frozendict

import fabricio

from .base import BaseService, Option, Attribute
from .container import Container

_service_data = {}


class RemovableOption(Option):

    get_values = '[]'.format

    def __init__(self, func=None, get_values=None, **kwargs):
        super(RemovableOption, self).__init__(func=func, **kwargs)
        self.get_values = get_values or self.get_values

    def get_current_values(self, service):
        info = _service_data['info'] = _service_data.get('info') or service.info
        values_data = self.get_values(info)
        values_data = values_data.replace("'", '"').replace('u"', '"')
        return json.loads(values_data)

    def get_remove_values(self, service):
        current_values = self.get_current_values(service)
        if not current_values:
            return None
        new_values = self.get_add_values(service)
        if isinstance(new_values, six.string_types):
            new_values = [new_values]
        return set(current_values).difference(new_values)

    def get_add_values(self, service):
        return self.__get__(service)


class Port(RemovableOption):

    get_values = '{0[Spec][EndpointSpec][Ports]!r}'.format


class Mount(RemovableOption):

    get_values = '{0[Spec][TaskTemplate][ContainerSpec][Mounts]!r}'.format


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

    replicas = Option(default=1)

    mount = Mount()

    network = Option()

    restart_condition = Option(name='restart-condition')

    @Option(name='stop-grace-period')
    def stop_timeout(self):
        return self.sentinel and self.sentinel.stop_timeout

    @RemovableOption(
        get_values='{0[Spec][TaskTemplate][ContainerSpec][Env]!r}'.format,
    )
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
                    name = option.name or attr
                    if isinstance(option, RemovableOption):
                        options[name + '-rm'] = option.get_remove_values
                        options[name + '-add'] = option.get_add_values
                    else:
                        options[name] = option.__get__
        return options

    @property
    def update_options(self):
        try:
            return frozendict(
                (
                    (option, callback(self))
                    for option, callback in self._update_options.items()
                ),
                image=self.image,
                args=self.args,
            )
        finally:
            _service_data.clear()

    def _update(self):
        try:
            pass
            # TODO find if service exists
            # service_spec = json.loads(fabricio.run(
            #     "docker service inspect --format '{{{{json .Spec}}}}' "
            #     "{service}".format(
            #         service=self,
            #     ),
            # ))
        except RuntimeError:
            self._create()
        else:
            fabricio.run('docker service update {options} {service}'.format(
                options=self.update_options,
                service=self,
            ))

    def _create(self):
        pass  # TODO
        # TODO command += args

    def update(self, tag=None, registry=None, force=False):
        if not self.is_manager():
            return False
        sentinel_updated = self.sentinel.update(
            tag=tag,
            registry=registry,
            force=force,
            run=False,
        )
        if not sentinel_updated:
            return False
        if self.is_leader():
            self._update()
        return True

    def revert(self):
        pass  # TODO

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

    @property
    def info(self):
        command = 'docker service inspect {service}'
        try:
            info = fabricio.run(command.format(service=self))
        except RuntimeError:
            raise RuntimeError(
                "Service '{service}' not found or host is "
                "not a swarm manager".format(service=self)
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
        # 'docker node inspect self' command works only on manager nodes
        return self._leader_status.succeeded

    def is_leader(self):
        return self._leader_status == 'true'
