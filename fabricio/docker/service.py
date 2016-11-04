from .base import BaseService, Option, Attribute
from .container import Container


class Service(BaseService):

    sentinel = None

    @Attribute
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

    def __init__(self, name, sentinel=None, options=None, **attrs):
        super(Service, self).__init__(name, options=options, **attrs)
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
