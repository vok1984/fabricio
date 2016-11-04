from cached_property import cached_property
from frozendict import frozendict

from fabricio.utils import default_property


class Option(default_property):

    def __init__(self, func=None, default=None, name=None):
        super(Option, self).__init__(func=func, default=default)
        self.name = name


class Attribute(default_property):
    pass


class BaseService(object):

    def __init__(self, name, options=None, **attrs):
        self.name = name

        options = options or {}
        self.overridden_options = set()
        is_main_option = self._main_options.__contains__
        self._additional_options = additional_options = {}
        for option, value in options.items():
            if is_main_option(option):
                setattr(self, option, value)
            else:
                additional_options[option] = value

        self.overridden_attributes = set()
        is_attribute = self._attributes.__contains__
        if attrs:
            for attr, value in attrs.items():
                if not is_attribute(attr):
                    raise TypeError(
                        'Unknown attribute: {attr}'.format(attr=attr)
                    )
                setattr(self, attr, value)

    def __setattr__(self, attr, value):
        if attr in self._main_options:
            self.overridden_options.add(attr)
        elif attr in self._attributes:
            self.overridden_attributes.add(attr)
        super(BaseService, self).__setattr__(attr, value)

    @cached_property
    def _main_options(self):
        return dict(
            (attr, value.name or attr)
            for cls in type(self).__mro__[::-1]
            for attr, value in vars(cls).items()
            if isinstance(value, Option)
        )

    @cached_property
    def _attributes(self):
        return set(
            attr
            for cls in type(self).__mro__
            for attr, value in vars(cls).items()
            if isinstance(value, Attribute)
        )

    def _get_options(self, **override):
        return frozendict(
            (
                (option, override.get(attr, getattr(self, attr)))
                for attr, option in self._main_options.items()
            ),
            **self._additional_options
        )

    options = property(_get_options)

    def fork(self, name=None, options=None, **attrs):
        if name is None:
            name = self.name

        fork_options = dict(
            (
                (option, getattr(self, option))
                for option in self.overridden_options
            ),
            **self._additional_options
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

    def update(self, tag=None, registry=None, force=False):
        raise NotImplementedError

    def revert(self):
        raise NotImplementedError

    def migrate(self, tag=None, registry=None):
        pass

    def migrate_back(self):
        pass

    def backup(self):
        pass

    def restore(self, backup_name=None):
        pass
