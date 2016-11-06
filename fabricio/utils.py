import contextlib

from copy import copy
from distutils import util as distutils

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import six


@contextlib.contextmanager
def patch(obj, attr, value, default=None):
    original = getattr(obj, attr, default)
    setattr(obj, attr, value)
    yield
    setattr(obj, attr, original)


class default_property(object):

    def __init__(self, func=None, default=None):
        self.func = func
        if func is not None:
            self.__doc__ = func.__doc__
        self.default = default

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.func is None:
            return self.default
        return self.func(instance)

    def __call__(self, func):
        clone = copy(self)
        clone.func = func
        return clone


class Options(OrderedDict):

    @staticmethod
    def make_option(option, value=None):
        option = '--' + option
        if value is not None:
            # TODO escape value
            option += ' ' + value
        return option

    def make_options(self):
        for option, value in self.items():
            if value is None:
                continue
            if isinstance(value, bool):
                if value is True:
                    yield self.make_option(option)
            elif isinstance(value, six.string_types):
                yield self.make_option(option, value)
            elif isinstance(value, six.integer_types):
                yield self.make_option(option, str(value))
            else:
                try:
                    values = iter(value)
                except TypeError:
                    yield self.make_option(option, str(value))
                else:
                    for single_value in values:
                        yield self.make_option(option, single_value)

    def __str__(self):
        return ' '.join(self.make_options())


def strtobool(value):
    return bool(distutils.strtobool(str(value)))


class Item(six.text_type):

    def __hash__(self):
        return hash(self.get_comparison_value())

    def __eq__(self, other):
        return self.get_comparison_value() == other

    def get_comparison_value(self):
        raise NotImplementedError
