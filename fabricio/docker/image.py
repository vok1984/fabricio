import functools
import json
import warnings

from cached_property import cached_property
from docker import utils as docker_utils, auth as docker_auth

import fabricio

from fabricio.utils import Options


class Image(object):

    def __init__(self, name=None, tag=None, registry=None):
        if name:
            _registry, _name, _tag = self.parse_image_name(name)
            self.name = _name
            self.tag = tag or _tag or 'latest'  # TODO 'latest' is unnecessary
            self.registry = registry or _registry
        else:
            self.name = name
            self.tag = tag
            self.registry = registry
        self.field_names = {}
        self.container = None

    def __str__(self):
        if self.container is not None:
            return self.id
        return repr(self)

    def __repr__(self):
        if self.registry:
            return '{registry}/{name}:{tag}'.format(
                registry=self.registry,
                name=self.name,
                tag=self.tag,
            )
        return '{name}:{tag}'.format(name=self.name, tag=self.tag)

    def __get__(self, container, owner_cls):
        if container is None:
            return self
        field_name = self.get_field_name(owner_cls)
        image = container.__dict__.get(field_name)
        if image is None:
            image = container.__dict__[field_name] = self.__class__(
                name=self.name,
                tag=self.tag,
                registry=self.registry,
            )
        # this cause circular reference between container and image, but it's
        # not a problem due to temporary nature of Fabric runtime
        image.container = container
        return image

    def __set__(self, container, image):
        field_name = self.get_field_name(type(container))
        container.__dict__[field_name] = (
            image[:]  # actually this means copy of image
            if isinstance(image, Image) else
            self.__class__(name=image)
        )

    def __getitem__(self, item):
        if isinstance(item, slice):
            registry, tag = item.start, item.stop
        else:
            registry, tag = None, item
        return self.__class__(
            name=self.name,
            tag=tag or self.tag,
            registry=registry or self.registry,
        )

    def get_field_name(self, owner_cls):
        field_name = self.field_names.get(owner_cls)
        if field_name is None:
            for attr in dir(owner_cls):
                if getattr(owner_cls, attr) is self:
                    if field_name is not None:
                        raise ValueError(
                            'Same instance of Image used for more than one '
                            'attributes of class {cls}'.format(
                                cls=owner_cls.__name__,
                            )
                        )
                    self.field_names[owner_cls] = field_name = attr
        return field_name

    @staticmethod
    def parse_image_name(image):
        repository, tag = docker_utils.parse_repository_tag(image)
        registry, name = docker_auth.resolve_repository_name(repository)
        if registry == docker_auth.INDEX_NAME:
            registry = ''
        return registry, name, tag

    @classmethod
    def make_container_options(cls, temporary=None, name=None, options=()):
        return Options(
            options,
            name=name,
            rm=temporary,
            tty=temporary,
            interactive=temporary,
            detach=temporary is not None and not temporary,
        )

    @property
    def info(self):
        command = 'docker inspect --type image {image}'
        try:
            info = fabricio.run(command.format(image=self))
        except RuntimeError:
            raise RuntimeError("Image '{image}' not found".format(image=self))
        return json.loads(str(info))[0]

    @cached_property
    def id(self):
        if self.container is None:
            return self.info['Id']
        return self.container.info['Image']

    def get_delete_callback(self, force=False):
        command = 'docker rmi {force}{image}'
        force = force and '--force ' or ''
        return functools.partial(
            fabricio.run,
            command.format(image=self, force=force),
            ignore_errors=True,
        )

    def delete(self, force=False, ignore_errors=True, deferred=False):
        delete_callback = self.get_delete_callback(force=force)
        if deferred:
            warnings.warn(
                'deferred argument is deprecated and will be removed in v0.4, '
                'use get_delete_callback() instead',
                category=RuntimeWarning, stacklevel=2,
            )
            return delete_callback
        return delete_callback(ignore_errors=ignore_errors)

    def run(
        self,
        cmd=None,  # deprecated
        command=None,
        temporary=True,
        quiet=True,
        name=None,
        options=(),
        **kwargs  # deprecated
    ):
        if kwargs:
            warnings.warn(
                'Container options must be provided in `options` arg, '
                'kwargs behavior will be removed in v0.4',
                category=RuntimeWarning, stacklevel=2,
            )
            options = dict(options, **kwargs)
        if cmd:
            warnings.warn(
                "'cmd' argument deprecated and will be removed in v0.4, "
                "use 'command' instead",
                category=RuntimeWarning, stacklevel=2,
            )
        run_command = 'docker run {options} {image} {command}'
        return fabricio.run(
            run_command.format(
                image=self,
                command=command or cmd or '',
                options=self.make_container_options(
                    temporary=temporary,
                    name=name,
                    options=options,
                ),
            ),
            quiet=quiet,
        )
