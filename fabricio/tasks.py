import collections
import contextlib
import functools
import os
import sys
import types
import warnings

from fabric import api as fab, colors
from fabric.contrib import console
from fabric.main import is_task_object
from fabric.tasks import WrappedCallableTask

import fabricio

from fabricio import docker
from fabricio.docker.base import LockImpossible
from fabricio.utils import patch, strtobool, Options, OrderedDict

__all__ = [
    'infrastructure',
    'skip_unknown_host',
    'DockerTasks',
    'PullDockerTasks',
    'BuildDockerTasks',
]


def skip_unknown_host(task):
    @functools.wraps(task)
    def _task(*args, **kwargs):
        if fab.env.get('host_string', False):
            return task(*args, **kwargs)
        fabricio.log('task `{task}` skipped (no host provided)'.format(
            task=fab.env.command,
        ))
    _task.wrapped = task  # compatibility with '--display <task>' option
    return _task


class IgnoreHostsTask(WrappedCallableTask):

    hosts = roles = property(lambda self: (), lambda self, value: None)


class Tasks(object):

    @property
    def __name__(self):
        return self

    __class__ = types.ModuleType

    def __new__(cls, *args, **kwargs):
        self = super(Tasks, cls).__new__(cls)
        for attr in dir(cls):
            attr_value = getattr(cls, attr)
            if is_task_object(attr_value):
                task_decorator = fab.task(
                    default=attr_value.is_default,
                    name=attr_value.name,
                    aliases=attr_value.aliases,
                    task_class=attr_value.__class__,
                )
                bounded_task = functools.partial(attr_value.wrapped, self)
                task = task_decorator(functools.wraps(attr_value)(bounded_task))
                for wrapped_attr in ['parallel', 'serial', 'pool_size']:
                    if hasattr(attr_value.wrapped, wrapped_attr):
                        setattr(
                            task.wrapped,
                            wrapped_attr,
                            getattr(attr_value.wrapped, wrapped_attr),
                        )
                setattr(self, attr, task)
        return self

    def __init__(self, roles=(), hosts=(), create_default_roles=True):
        if create_default_roles:
            for role in roles:
                fab.env.roledefs.setdefault(role, [])
        for task in self:
            task.roles = roles
            task.hosts = hosts

    def __iter__(self):
        for name, attr_value in vars(self).items():
            if is_task_object(attr_value):
                yield attr_value


class Infrastructure(Tasks):

    def __new__(cls, *args, **kwargs):
        if len(args) > 1:
            raise ValueError('only 1 positional argument allowed')
        if not args:
            return lambda callback: cls(callback, **kwargs)
        return super(Infrastructure, cls).__new__(cls, *args, **kwargs)

    def __init__(
        self,
        callback=None,
        color=colors.yellow,
        name=None,
        *args, **kwargs
    ):
        super(Infrastructure, self).__init__(*args, **kwargs)
        # We need to be sure that `default()` will be at first place
        # every time when vars(self) is being invoked.
        # See Fabric's `extract_tasks()`
        self.__dict__ = OrderedDict(
            (('default', self.default), ),
            **self.__dict__
        )
        self.callback = callback
        self.color = color
        self.name = name = name or callback.__name__
        name = color(name)
        self.default.__doc__ = self.default.__doc__.format(name=name)
        self.confirm.__doc__ = self.confirm.__doc__.format(name=name)

    @fab.task(default=True, name='confirm')
    def default(self, *args, **kwargs):
        """
        select {name} infrastructure to run task(s) on
        """
        if not console.confirm(
            'Are you sure you want to select {name} '
            'infrastructure to run task(s) on?'.format(
                name=self.color(self.name),
            ),
            default=False,
        ):
            fab.abort('Aborted')
        self.confirm(*args, **kwargs)

    @fab.task
    def confirm(self, *args, **kwargs):
        """
        automatically confirm {name} infrastructure selection
        """
        fab.env.infrastructure = self.name
        self.callback(*args, **kwargs)

infrastructure = Infrastructure


class _DockerTasks(Tasks):

    def __init__(
        self,
        service=None,
        container=None,  # deprecated
        registry=None,
        migrate_commands=False,
        backup_commands=False,
        **kwargs
    ):
        if container:
            warnings.warn(
                "'container' argument is deprecated and will be removed "
                "in v0.4, use 'service' instead",
                category=RuntimeWarning, stacklevel=2,
            )
        super(_DockerTasks, self).__init__(**kwargs)
        self.registry = docker.Registry(registry)
        self.service = service or container
        self.backup.use_task_objects = backup_commands
        self.restore.use_task_objects = backup_commands
        self.migrate.use_task_objects = migrate_commands
        self.migrate_back.use_task_objects = migrate_commands
        self.revert.use_task_objects = False  # disabled in favour of rollback
        self._locks = collections.defaultdict(set)

    @property
    def image(self):
        return self.service.image

    @fab.task
    @skip_unknown_host
    def revert(self):
        """
        revert Docker container to previous version
        """
        self.service.revert()

    @contextlib.contextmanager
    def exclusive_lock(self, callback):
        if fab.env.parallel:
            raise TypeError('Cannot use exclusive_lock in parallel mode')
        if callback in self._locks[fab.env.infrastructure]:
            raise LockImpossible
        self._locks[fab.env.infrastructure].add(callback)
        yield

    def execute_with_lock(self, *args, **kwargs):
        try:
            callback, args = args[0], args[1:]
        except IndexError:
            raise ValueError('Must provide callback argument')
        if fab.env.parallel:
            lock = self.service.lock()
        else:
            lock = self.exclusive_lock(callback)
        try:
            with lock:
                return callback(*args, **kwargs)
        except LockImpossible:
            pass

    @fab.task
    @skip_unknown_host
    def migrate(self, tag=None):
        """
        apply migrations
        """
        self.execute_with_lock(
            self.service.migrate,
            tag=tag,
            registry=self.registry,
        )

    @fab.task
    @skip_unknown_host
    def migrate_back(self):
        """
        remove previously applied migrations if any
        """
        self.execute_with_lock(self.service.migrate_back)

    @fab.task
    @skip_unknown_host
    def backup(self):
        """
        backup data
        """
        self.execute_with_lock(self.service.backup)

    @fab.task
    @skip_unknown_host
    def restore(self, backup_filename=None):
        """
        restore data
        """
        self.execute_with_lock(
            self.service.restore,
            backup_name=backup_filename,
        )

    @fab.task(task_class=IgnoreHostsTask)
    def rollback(self, migrate_back=True):
        """
        rollback Docker container to previous version
        """
        if strtobool(migrate_back):
            fab.execute(self.migrate_back)
        fab.execute(self.revert)

    @fab.task
    @skip_unknown_host
    def pull(self, tag=None):
        """
        pull Docker image from registry
        """
        self.service.pull_image(tag=tag, registry=self.registry)

    @fab.task
    @skip_unknown_host
    def update(self, tag=None, force=False):
        """
        update the service / container
        """
        updated = self.service.update(
            tag=tag,
            registry=self.registry,
            force=strtobool(force),
        )
        if not updated:
            fabricio.log('Host does not require update, update skipped.')

    @fab.task(default=True, task_class=IgnoreHostsTask)
    def deploy(self, tag=None, force=False, migrate=True, backup=False):
        """
        backup -> pull -> migrate -> update
        """
        if strtobool(backup):
            fab.execute(self.backup)
        fab.execute(self.pull, tag=tag)
        if strtobool(migrate):
            fab.execute(self.migrate, tag=tag)
        fab.execute(self.update, tag=tag, force=force)


class PullDockerTasks(_DockerTasks):

    def __init__(
        self,
        registry='localhost:5000',
        local_registry='localhost:5000',
        use_ssh_tunnel=True,
        **kwargs
    ):
        warnings.warn(
            'PullDockerTasks is deprecated and will be removed in v0.4, '
            'use DockerTasks instead', DeprecationWarning,
        )
        warnings.warn(
            'PullDockerTasks is deprecated and will be removed in v0.4, '
            'use DockerTasks instead', category=RuntimeWarning, stacklevel=2,
        )
        super(PullDockerTasks, self).__init__(registry=registry, **kwargs)
        self.local_registry = docker.Registry(local_registry)
        self.use_ssh_tunnel = use_ssh_tunnel

    @property
    def tunnel_required(self):
        if not self.use_ssh_tunnel:
            return False
        if self.registry.host in ['localhost', '127.0.0.1']:
            return True
        command = (
            'getent -V > /dev/null '
            '&& getent hosts {host} '
            '| head -1 '
            '| awk \'{{ print $1 }}\''
        ).format(
            host=self.registry.host,
        )
        try:
            result = fabricio.run(command, use_cache=True)
            return result in ['127.0.0.1', '::1']
        except RuntimeError:
            fab.abort(
                'It seems that \'{host}\' host misses `getent` command, '
                'please install it and try again'.format(
                    host=fab.env.host,
                )
            )

    @fab.task(task_class=IgnoreHostsTask)
    def push(self, tag=None):
        """
        push Docker image to registry
        """
        local_tag = str(self.image[self.local_registry:tag])
        fabricio.local(
            'docker tag {image} {tag}'.format(
                image=self.image[tag],
                tag=local_tag,
            ),
            use_cache=True,
        )
        fabricio.local(
            'docker push {tag}'.format(tag=local_tag),
            quiet=False,
            use_cache=True,
        )
        fabricio.local(
            'docker rmi {tag}'.format(tag=local_tag),
            use_cache=True,
        )

    @fab.task
    @skip_unknown_host
    def pull(self, tag=None):
        """
        pull Docker image from registry
        """
        if self.tunnel_required:
            with contextlib.closing(open(os.devnull, 'w')) as output:
                with patch(sys, 'stdout', output):
                    # forward sys.stdout to os.devnull to prevent
                    # printing debug messages by fab.remote_tunnel

                    with fab.remote_tunnel(
                        remote_port=self.registry.port,
                        local_port=self.local_registry.port,
                        local_host=self.local_registry.host,
                    ):
                        _DockerTasks.pull(self, tag=tag)
        else:
            _DockerTasks.pull(self, tag=tag)

    @fab.task(task_class=IgnoreHostsTask)
    def prepare(self, tag=None):
        """
        prepare Docker image
        """
        fabricio.local(
            'docker pull {image}'.format(image=self.image[tag]),
            quiet=False,
            use_cache=True,
        )
        self.delete_dangling_images()

    @fab.task(default=True, task_class=IgnoreHostsTask)
    def deploy(self, tag=None, force=False, migrate=True, backup=False):
        """
        prepare -> push -> backup -> pull -> migrate -> update
        """
        fab.execute(self.prepare, tag=tag)
        fab.execute(self.push, tag=tag)
        _DockerTasks.deploy(
            self, tag=tag, force=force, migrate=migrate, backup=backup)

    @staticmethod
    def delete_dangling_images():
        fabricio.local(
            'for img in $(docker images --filter "dangling=true" --quiet); '
            'do docker rmi "$img"; done'
        )

    def remove_obsolete_images(self):
        warnings.warn(
            'remove_obsolete_images() renamed to delete_dangling_images()',
            DeprecationWarning,
        )
        self.delete_dangling_images()


class DockerTasks(Tasks):

    def __init__(
        self,
        service=None,
        container=None,  # deprecated
        registry=None,
        ssh_tunnel_port=None,
        migrate_commands=False,
        backup_commands=False,
        **kwargs
    ):
        if container:
            warnings.warn(
                "'container' argument is deprecated and will be removed "
                "in v0.4, use 'service' instead",
                category=RuntimeWarning, stacklevel=2,
            )
        super(DockerTasks, self).__init__(**kwargs)
        self.service = service or container
        self.registry = docker.Registry(registry)
        self.host_registry = docker.Registry(
            'localhost:{port}'.format(port=ssh_tunnel_port)
            if ssh_tunnel_port else
            registry
        )
        self.backup.use_task_objects = backup_commands
        self.restore.use_task_objects = backup_commands
        self.migrate.use_task_objects = migrate_commands
        self.migrate_back.use_task_objects = migrate_commands
        self.revert.use_task_objects = False  # disabled in favour of rollback
        self.prepare.use_task_objects = registry is not None
        self.push.use_task_objects = registry is not None
        self._locks = collections.defaultdict(set)

    @property
    def image(self):
        return self.service.image

    @fab.task
    @skip_unknown_host
    def revert(self):
        """
        revert Docker container to previous version
        """
        self.service.revert()

    @contextlib.contextmanager
    def exclusive_lock(self, callback):
        if fab.env.parallel:
            raise TypeError('Cannot use exclusive_lock in parallel mode')
        if callback in self._locks[fab.env.infrastructure]:
            raise LockImpossible
        self._locks[fab.env.infrastructure].add(callback)
        yield

    def execute_with_lock(self, *args, **kwargs):
        try:
            callback, args = args[0], args[1:]
        except IndexError:
            raise ValueError('Must provide callback argument')
        if fab.env.parallel:
            lock = self.service.lock()
        else:
            lock = self.exclusive_lock(callback)
        try:
            with lock:
                return callback(*args, **kwargs)
        except LockImpossible:
            pass

    @fab.task
    @skip_unknown_host
    def migrate(self, tag=None):
        """
        apply migrations
        """
        self.execute_with_lock(
            self.service.migrate,
            tag=tag,
            registry=self.host_registry,
        )

    @fab.task
    @skip_unknown_host
    def migrate_back(self):
        """
        remove previously applied migrations if any
        """
        self.execute_with_lock(self.service.migrate_back)

    @fab.task
    @skip_unknown_host
    def backup(self):
        """
        backup data
        """
        self.execute_with_lock(self.service.backup)

    @fab.task
    @skip_unknown_host
    def restore(self, backup_filename=None):
        """
        restore data
        """
        self.execute_with_lock(
            self.service.restore,
            backup_name=backup_filename,
        )

    @fab.task(task_class=IgnoreHostsTask)
    def rollback(self, migrate_back=True):
        """
        rollback Docker container to previous version
        """
        if strtobool(migrate_back):
            fab.execute(self.migrate_back)
        fab.execute(self.revert)

    @fab.task(task_class=IgnoreHostsTask)
    def prepare(self, tag=None):
        """
        prepare Docker image
        """
        if self.registry is None:
            return
        fabricio.local(
            'docker pull {image}'.format(image=self.image[tag]),
            quiet=False,
            use_cache=True,
        )
        self.delete_dangling_images()

    @staticmethod
    def delete_dangling_images():
        if os.name == 'posix':
            # macOS, Linux, etc.
            fabricio.local(
                'for img in $(docker images --filter "dangling=true" --quiet); '
                'do docker rmi "$img"; done'
            )
        elif os.name == 'nt':
            # Windows
            fabricio.local(
                "for /F %i in ('docker images --filter \"dangling=true\" "
                "--quiet') do @docker rmi %i"
            )

    def push_image(self, tag=None):
        fabricio.local(
            'docker push {image}'.format(image=self.image[self.registry:tag]),
            quiet=False,
            use_cache=True,
        )

    @fab.task(task_class=IgnoreHostsTask)
    def push(self, tag=None):
        """
        push Docker image to registry
        """
        if self.registry is None:
            return
        tag_with_registry = str(self.image[self.registry:tag])
        fabricio.local(
            'docker tag {image} {tag}'.format(
                image=self.image[tag],
                tag=tag_with_registry,
            ),
            use_cache=True,
        )
        self.push_image(tag=tag)
        fabricio.local(
            'docker rmi {tag}'.format(tag=tag_with_registry),
            use_cache=True,
        )

    def pull_image(self, tag=None):
        image = self.image[self.host_registry:tag]
        fabricio.run(
            'docker pull {image}'.format(image=image),
            quiet=False,
        )

    @fab.task
    @skip_unknown_host
    def pull(self, tag=None):
        """
        pull Docker image from registry
        """
        if self.host_registry and self.host_registry.host == 'localhost':
            if self.registry:
                local_port = self.registry.port
                local_host = self.registry.host
            elif self.image.registry:
                local_port = self.image.registry.port
                local_host = self.image.registry.host
            else:
                raise ValueError(
                    'Either local host or local port for SSH tunnel '
                    'can not be obtained'
                )
            with contextlib.closing(open(os.devnull, 'w')) as output:
                with patch(sys, 'stdout', output):
                    # forward sys.stdout to os.devnull to prevent
                    # printing debug messages by fab.remote_tunnel

                    with fab.remote_tunnel(
                        remote_port=self.host_registry.port,
                        local_port=local_port,
                        local_host=local_host,
                    ):
                        self.pull_image(tag=tag)
        else:
            self.pull_image(tag=tag)

    @fab.task
    @skip_unknown_host
    def update(self, tag=None, force=False):
        """
        start new Docker container if necessary
        """
        updated = self.service.update(
            tag=tag,
            registry=self.host_registry,
            force=strtobool(force),
        )
        if not updated:
            fabricio.log('No changes detected, update skipped.')

    @fab.task(default=True, task_class=IgnoreHostsTask)
    def deploy(
        self,
        tag=None,
        force=False,
        prepare=True,
        backup=False,
        migrate=True,
    ):
        """
        prepare -> push -> backup -> pull -> migrate -> update
        """
        if strtobool(prepare):
            fab.execute(self.prepare, tag=tag)
            fab.execute(self.push, tag=tag)
        if strtobool(backup):
            fab.execute(self.backup)
        fab.execute(self.pull, tag=tag)
        if strtobool(migrate):
            fab.execute(self.migrate, tag=tag)
        fab.execute(self.update, tag=tag, force=force)


class BuildDockerTasks(PullDockerTasks):

    def __init__(self, build_path='.', **kwargs):
        warnings.warn(
            'BuildDockerTasks is deprecated and will be removed in v0.4, '
            'use ImageBuildDockerTasks instead', DeprecationWarning,
        )
        warnings.warn(
            'BuildDockerTasks is deprecated and will be removed in v0.4, '
            'use ImageBuildDockerTasks instead',
            category=RuntimeWarning, stacklevel=2,
        )
        super(BuildDockerTasks, self).__init__(**kwargs)
        self.build_path = build_path

    @fab.task(task_class=IgnoreHostsTask)
    def prepare(self, tag=None, no_cache=False):
        """
        prepare Docker image
        """
        options = Options([
            ('tag', self.image[tag]),
            ('no-cache', strtobool(no_cache)),
            ('pull', True),
        ])
        fabricio.local(
            'docker build {options} {build_path}'.format(
                build_path=self.build_path,
                options=options,
            ),
            quiet=False,
            use_cache=True,
        )
        self.delete_dangling_images()

    @fab.task(default=True, task_class=IgnoreHostsTask)
    def deploy(
        self,
        tag=None,
        force=False,
        migrate=True,
        backup=False,
        no_cache=False,
    ):
        """
        prepare -> push -> backup -> pull -> migrate -> update
        """
        fab.execute(self.prepare, tag=tag, no_cache=no_cache)
        fab.execute(self.push, tag=tag)
        _DockerTasks.deploy(
            self,
            tag=tag,
            force=force,
            migrate=migrate,
            backup=backup,
        )


class ImageBuildDockerTasks(DockerTasks):

    def __init__(self, service=None, container=None, build_path='.', **kwargs):
        super(ImageBuildDockerTasks, self).__init__(service, container, **kwargs)
        self.build_path = build_path
        self.prepare.use_task_objects = True
        self.push.use_task_objects = True

    @fab.task(task_class=IgnoreHostsTask)
    def prepare(self, tag=None, no_cache=False):
        """
        prepare Docker image
        """
        options = Options([
            ('tag', self.image[self.registry:tag]),
            ('no-cache', strtobool(no_cache)),
            ('pull', True),
        ])
        fabricio.local(
            'docker build {options} {build_path}'.format(
                build_path=self.build_path,
                options=options,
            ),
            quiet=False,
            use_cache=True,
        )
        self.delete_dangling_images()

    @fab.task(task_class=IgnoreHostsTask)
    def push(self, tag=None):
        """
        push Docker image to registry
        """
        self.push_image(tag=tag)
