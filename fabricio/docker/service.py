from .base import BaseService, Option, Attribute


class Service(BaseService):

    @property
    def image(self):
        return self.container.image

    @Attribute
    def cmd(self):
        return self.container.cmd

    replicas = Option(default=1)

    mount = Option()

    @Option
    def env(self):
        return self.container.env

    @Option
    def network(self):
        return self.container.network

    @Option
    def ports(self):
        return self.container.ports

    @Option
    def user(self):
        return self.container.user

    def __init__(self, name, container=None, options=None, **attrs):
        super(Service, self).__init__(name, options=options, **attrs)
        self.container = container

    def fork(self, name=None, container=None, options=None, **attrs):
        container = container or self.container
        return super(Service, self).fork(
            name,
            container=container,
            options=options,
            **attrs
        )
