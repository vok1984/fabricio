import json
import warnings

import fabricio

from .base import BaseService, Option, Attribute
from .image import Image


class ContainerNotFoundError(RuntimeError):
    pass


class Container(BaseService):

    image = Image()

    @Attribute
    def cmd(self):
        warnings.warn(
            "'cmd' is deprecated and will be removed in ver. 0.4, "
            "use 'command' instead", DeprecationWarning,
        )
        return None

    @Attribute
    def command(self):
        command = self.cmd
        if command:
            warnings.warn(
                "'cmd' is deprecated and will be removed in ver. 0.4, "
                "use 'command' instead", RuntimeWarning,
            )
        return command

    stop_timeout = Attribute(default=10)

    user = Option()
    ports = Option(name='publish')
    env = Option()
    volumes = Option(name='volume')
    links = Option(name='link')
    hosts = Option(name='add-host')
    network = Option(name='net')
    restart_policy = Option(name='restart')
    stop_signal = Option(name='stop-signal')

    def __init__(self, _name=None, image=None, options=None, **attrs):
        if _name:
            warnings.warn(
                'Passing container name using positional argument is '
                'deprecated, this behaviour will be removed in v0.4, '
                'use `name` keyword instead',
                category=RuntimeWarning, stacklevel=2,
            )
            attrs.update(name=_name)
        super(Container, self).__init__(options=options, **attrs)
        if image is not None:
            self.image = image

    @property
    def safe_options(self):
        return self._get_options(ports=None)

    def fork(self, _name=None, image=None, options=None, **attrs):
        if _name:
            warnings.warn(
                'Passing container name using positional argument is '
                'deprecated, this behaviour will be removed in v0.4, '
                'use `name` keyword instead',
                category=RuntimeWarning, stacklevel=2,
            )
            attrs.update(name=_name)
        image = image or self.image
        return super(Container, self).fork(
            image=image,
            options=options,
            **attrs
        )

    @property
    def info(self):
        command = 'docker inspect --type container {container}'
        info = fabricio.run(
            command.format(container=self),
            abort_exception=ContainerNotFoundError,
        )
        return json.loads(info)[0]

    def delete(
        self,
        force=False,
        delete_image=False,
        delete_dangling_volumes=True,
    ):
        delete_image_callback = None
        if delete_image:
            delete_image_callback = self.image.get_delete_callback()
        command = 'docker rm {force}{container}'
        force = force and '--force ' or ''
        fabricio.run(command.format(container=self, force=force))
        if delete_dangling_volumes:
            fabricio.run(
                'for volume in '
                '$(docker volume ls --filter "dangling=true" --quiet); '
                'do docker volume rm "$volume"; done'
            )
        if delete_image_callback:
            delete_image_callback()

    def run(self, tag=None, registry=None):
        self.image[registry:tag].run(
            command=self.command,
            temporary=False,
            name=self,
            options=self.options,
        )

    def create(self, tag=None, registry=None):
        self.image[registry:tag].create_container(
            command=self.command,
            name=self,
            options=self.options,
        )

    def execute(
        self,
        command=None,
        cmd=None,  # deprecated
        ignore_errors=False,
        quiet=True,
        use_cache=False,
    ):
        if cmd:
            warnings.warn(
                "'cmd' argument deprecated and will be removed in v0.4, "
                "use 'command' instead",
                category=RuntimeWarning, stacklevel=2,
            )
        if not (command or cmd):
            raise ValueError('Must provide command to execute')
        exec_command = 'docker exec --tty --interactive {container} {command}'
        return fabricio.run(
            exec_command.format(container=self, command=command or cmd),
            ignore_errors=ignore_errors,
            quiet=quiet,
            use_cache=use_cache,
        )

    def start(self):
        command = 'docker start {container}'
        fabricio.run(command.format(container=self))

    def stop(self, timeout=None):
        if timeout is None:
            timeout = self.stop_timeout
        command = 'docker stop --time {timeout} {container}'
        fabricio.run(command.format(container=self, timeout=timeout))

    def restart(self, timeout=None):
        if timeout is None:
            timeout = self.stop_timeout
        command = 'docker restart --time {timeout} {container}'
        fabricio.run(command.format(container=self, timeout=timeout))

    def rename(self, new_name):
        command = 'docker rename {container} {new_name}'
        fabricio.run(command.format(container=self, new_name=new_name))
        self.name = new_name

    def signal(self, signal):
        command = 'docker kill --signal {signal} {container}'
        fabricio.run(command.format(container=self, signal=signal))

    def update(self, tag=None, registry=None, force=False, run=True):
        if not force:
            try:
                current_image_id = self.image.id
            except ContainerNotFoundError:
                pass
            else:
                new_image = self.image[registry:tag]
                if current_image_id == new_image.id:
                    if run:
                        self.start()  # force starting container
                    return False
        new_container = self.fork(name=self.name)
        obsolete_container = self.get_backup_container()
        try:
            obsolete_container.delete(delete_image=True)
        except RuntimeError:
            pass  # backup container not found
        try:
            backup_container = self.fork()
            backup_container.rename(obsolete_container.name)
        except RuntimeError:
            pass  # current container not found
        else:
            backup_container.stop()
        if run:
            new_container.run(tag=tag, registry=registry)
        else:
            new_container.create(tag=tag, registry=registry)
        return True

    def revert(self):
        backup_container = self.get_backup_container()
        if not backup_container.info:
            return  # does backup container exist?
        self.stop()
        backup_container.start()
        self.delete(delete_image=True)
        backup_container.rename(self.name)

    def get_backup_container(self):
        return self.fork(name='{container}_backup'.format(container=self))

    def pull_image(self, tag=None, registry=None):
        self.image[registry:tag].pull()
