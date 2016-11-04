from fabricio.utils import default_property

from .base import BaseService, Option, Attribute
from .container import Container
from .image import Image


class Service(BaseService):

    sentinel = None

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

    def migrate(self, tag=None, registry=None):
        self.sentinel.migrate(tag=tag, registry=registry)

    def migrate_back(self):
        self.sentinel.migrate_back()

    def backup(self):
        self.sentinel.backup()

    def restore(self, backup_name=None):
        self.sentinel.restore(backup_name=backup_name)
