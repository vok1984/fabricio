import dummy_threading

from fabric import api as fab, colors

import fabricio

from fabricio.utils import default_property

from .base import BaseService, Option, Attribute
from .container import Container
from .image import Image


class Service(BaseService):

    sentinel = None

    lock = dummy_threading.RLock()  # allow all tasks to be executed in parallel

    @default_property
    def image(self):
        return self.sentinel and self.sentinel.image

    @Attribute
    def command(self):
        return self.sentinel and self.sentinel.command

    args = Attribute()

    replicas = Option(default=1)

    mount = Option()

    network = Option()

    restart_condition = Option(name='restart-condition')

    @Option(name='stop-grace-period')
    def stop_timeout(self):
        return self.sentinel and self.sentinel.stop_timeout

    @Option
    def env(self):
        return self.sentinel and self.sentinel.env

    @Option(name='publish')
    def ports(self):
        return self.sentinel and self.sentinel.ports

    @Option
    def user(self):
        return self.sentinel and self.sentinel.user

    def __init__(self, name, image=None, sentinel=None, options=None, **attrs):
        super(Service, self).__init__(name, options=options, **attrs)
        if image:
            self.image = image if isinstance(image, Image) else Image(image)
        self.sentinel = sentinel or Container(
            name=name,
            image=self.image,
            stop_timeout=self.stop_timeout,
            options=dict(
                env=self.env,
                user=self.user,
            ),
        )

    def fork(self, name=None, sentinel=None, options=None, **attrs):
        sentinel = sentinel or self.sentinel
        return super(Service, self).fork(
            name,
            sentinel=sentinel,
            options=options,
            **attrs
        )

    def update(self, tag=None, registry=None, force=False):
        # TODO check if this host is manager
        sentinel_updated = self.sentinel.update(
            tag=tag,
            registry=registry,
            force=force,
            run=False,
        )
        if not sentinel_updated:
            return False
        # TODO check if this host is a leader
        # TODO finish implementation

    def revert(self):
        pass  # TODO

    def pull_image(self, tag=None, registry=None):
        try:
            self.sentinel.pull_image(tag=tag, registry=registry)
        except RuntimeError as error:
            if self.is_manager():
                # inability to pull image is critical only for Swarm managers
                # because they have to keep up to date their sentinel containers
                raise
            fabricio.log(
                "{host} could not pull image: {error}".format(
                    host=fab.env.host,
                    error=error,
                ),
                color=colors.red,
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
    def _leader_status(self):
        command = "docker node inspect --format '{{.ManagerStatus.Leader}}' self"  # noqa
        return fabricio.run(command, ignore_errors=True, use_cache=True)

    def is_manager(self):
        return self._leader_status.succeeded

    def is_leader(self):
        return self._leader_status == 'true'
