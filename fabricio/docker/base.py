from cached_property import cached_property
from frozendict import frozendict

from fabricio.utils import default_property


class Option(default_property):
    pass


class Attribute(default_property):
    pass


class BaseService(object):

    def __init__(self, name, options=None, **attrs):
        self.name = name

        options = options or {}
        self.overridden_options = set()
        is_main_option = self.main_options.__contains__
        self.options = container_options = {}
        for option, value in options.items():
            if is_main_option(option):
                setattr(self, option, value)
            else:
                container_options[option] = value

        self.overridden_attributes = set()
        is_attribute = self.attributes.__contains__
        if attrs:
            for attr, value in attrs.items():
                if not is_attribute(attr):
                    raise TypeError(
                        'Unknown attribute: {attr}'.format(attr=attr)
                    )
                setattr(self, attr, value)

    def __setattr__(self, attr, value):
        if attr in self.main_options:
            self.overridden_options.add(attr)
        elif attr in self.attributes:
            self.overridden_attributes.add(attr)
        super(BaseService, self).__setattr__(attr, value)

    def _get_options(self):
        default_options_values = dict(
            (option, getattr(self, option))
            for option in self.main_options
        )
        return frozendict(self._options, **default_options_values)

    def _set_options(self, options):
        self._options = options

    options = property(_get_options, _set_options)

    @cached_property
    def main_options(self):
        return set(
            attr
            for cls in type(self).__mro__
            for attr, value in vars(cls).items()
            if isinstance(value, Option)
        )

    @cached_property
    def attributes(self):
        return set(
            attr
            for cls in type(self).__mro__
            for attr, value in vars(cls).items()
            if isinstance(value, Attribute)
        )

    def fork(self, name=None, options=None, **attrs):
        if name is None:
            name = self.name

        fork_options = dict(
            (
                (option, getattr(self, option))
                for option in self.overridden_options
            ),
            **self._options
        )
        if options:
            fork_options.update(options)

        if self.overridden_attributes:
            attrs = dict(
                (
                    (attr, getattr(self, attr))
                    for attr in self.overridden_attributes
                ),
                **attrs
            )

        return self.__class__(name, options=fork_options, **attrs)

    def __str__(self):
        return self.name

    def __copy__(self):
        return self.fork()
