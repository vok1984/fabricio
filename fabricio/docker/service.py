from .base import BaseService, Option, Attribute


class Service(BaseService):

    @Attribute
    def image(self):
        return self.container and self.container.image

    @Attribute
    def cmd(self):
        return self.container and self.container.cmd

    args = Attribute()

    replicas = Option(default=1)

    mount = Option()

    restart_condition = Option(name='restart-condition')

    @Option(name='stop-grace-period')
    def stop_timeout(self):
        return self.container and self.container.stop_timeout

    @Option
    def env(self):
        return self.container and self.container.env

    @Option
    def network(self):
        return self.container and self.container.network

    @Option(name='publish')
    def ports(self):
        return self.container and self.container.ports

    @Option
    def user(self):
        return self.container and self.container.user

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
