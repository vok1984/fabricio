from .base import BaseService, Option, Attribute


class Service(BaseService):

    def __init__(self, name, container=None, options=None, **attrs):
        super(Service, self).__init__(name, options=options, **attrs)
        self.container = container
