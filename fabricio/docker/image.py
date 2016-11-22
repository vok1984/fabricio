import functools
import json
import warnings

from docker import utils as docker_utils, auth as docker_auth

import fabricio

from fabricio import utils

from .registry import Registry


class ImageNotFoundError(RuntimeError):
    pass


class Image(object):

    def __init__(self, name=None, tag=None, registry=None):
        if name:
            _registry, _name, _tag = self.parse_image_name(name)
            self.name = _name
            self.tag = tag or _tag or 'latest'  # TODO 'latest' is unnecessary
            registry = registry or _registry
        else:
            self.name = name
            self.tag = tag
        self.registry = Registry(registry)
        self.field_names = {}
        self.container = None

    def __str__(self):
        if self.container is not None:
            return self.id
        return self.__repr__()

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
        # TODO every time new instance of image?
        field_name = self.get_field_name(owner_cls)
        image = container.__dict__.get(field_name)
        if image is None:
            image = container.__dict__[field_name] = self.__class__(
                name=self.name,
                tag=self.tag,
                registry=self.registry,
            )
        # this cause circular reference between container and image, but it
        # isn't an issue due to a temporary nature of Fabric runtime
        image.container = container
        return image

    def __set__(self, container, image):
        field_name = self.get_field_name(type(container))
        container.__dict__[field_name] = (
            image[:]  # actually this means copy of image
            if isinstance(image, Image) else
            self.__class__(image)
        )

    def __delete__(self, container):
        field_name = self.get_field_name(type(container))
        container.__dict__.pop(field_name, None)

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

    def __iter__(self):
        raise TypeError

    def get_field_name(self, owner_cls):
        # TODO think about result cache
        field_name = self.field_names.get(owner_cls)
        if field_name is None:
            for attr in dir(owner_cls):
                if getattr(owner_cls, attr) is self:
                    if field_name is not None:
                        raise ValueError(
                            'Same instance of Image used for more than one '
                            'attribute of class {cls}'.format(
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
            registry = None
        return registry, name, tag

    @classmethod
    def make_container_options(cls, temporary=None, name=None, options=()):
        additional_options = temporary and {
            'restart': None,  # temporary containers can't be restarted
        } or {}
        return utils.Options(
            options,
            name=name,
            rm=temporary,
            tty=temporary,
            interactive=temporary,
            detach=temporary is not None and not temporary,
            **additional_options
        )

    @property
    def digest(self):
        for repo_digest in self.info.get('RepoDigests', ()):
            return repo_digest
        return self.__str__()

    @property
    def info(self):
        command = 'docker inspect --type image {image}'
        info = fabricio.run(
            command.format(image=self),
            abort_exception=ImageNotFoundError,
        )
        return json.loads(str(info))[0]

    @property
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

    def create_container(
        self,
        command,
        name=None,
        options=(),
        quiet=True,
    ):
        run_command = 'docker create {options} {image} {command}'
        return fabricio.run(
            run_command.format(
                image=self,
                command=command or '',
                options=self.make_container_options(
                    name=name,
                    options=options,
                ),
            ),
            quiet=quiet,
        )

    def run(
        self,
        command=None,
        cmd=None,  # deprecated
        name=None,
        temporary=True,
        options=(),
        quiet=True,
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

    def pull(self):
        fabricio.run(
            'docker pull {image}'.format(image=self),
            quiet=False,
        )
