import contextlib
import re

from copy import copy
from distutils import util as distutils

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import six

from cached_property import cached_property
from fabric import api as fab

DEFAULT = object()


@contextlib.contextmanager
def patch(obj, attr, value, default=DEFAULT, force_delete=False):
    original = not force_delete and getattr(obj, attr, default)
    setattr(obj, attr, value)
    yield
    if force_delete or original is DEFAULT:
        obj.__delattr__(attr)
    else:
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

    quoting_required_regex = re.compile('[\s"\']+')

    def quote_option_value(self, value):
        if value and not self.quoting_required_regex.search(value):
            return value
        return '"{value}"'.format(value=value.replace('"', '\\"'))

    def make_option(self, option, value=None):
        option = '--' + option
        if value is not None:
            # TODO escape value
            option += ' ' + self.quote_option_value(value)
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


class host_cached_property(cached_property):

    def __get__(self, obj, cls):
        if obj is None:
            return self
        hosts = self.hosts(obj)
        try:
            return hosts[fab.env.host]
        except KeyError:
            value = hosts[fab.env.host] = self.func(obj)
        return value

    def __set__(self, obj, value):
        self.hosts(obj)[fab.env.host] = value

    def __delete__(self, obj):
        self.hosts(obj).pop(fab.env.host, None)

    def hosts(self, obj):
        return obj.__dict__.setdefault(self.func.__name__, {})
