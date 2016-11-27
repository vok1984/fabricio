# coding: utf-8
import collections
import mock
import re
import unittest2 as unittest

from fabric import api as fab

import fabricio

from fabricio import docker
from fabricio.docker.container import Option, Attribute
from tests import SucceededResult, docker_run_args_parser, \
    docker_service_update_args_parser, FailedResult, \
    docker_entity_inspect_args_parser, docker_inspect_args_parser, \
    docker_service_create_args_parser


class TestContainer(docker.Container):

    image = docker.Image('image:tag')


class ContainerTestCase(unittest.TestCase):

    def test_options(self):
        cases = dict(
            default=dict(
                kwargs=dict(),
                expected={
                    'net': None,
                    'link': None,
                    'stop-signal': None,
                    'restart': None,
                    'add-host': None,
                    'user': None,
                    'env': None,
                    'volume': None,
                    'publish': None,
                    'label': None,
                },
            ),
            custom=dict(
                kwargs=dict(options=dict(foo='bar')),
                expected={
                    'net': None,
                    'link': None,
                    'stop-signal': None,
                    'restart': None,
                    'add-host': None,
                    'user': None,
                    'env': None,
                    'volume': None,
                    'publish': None,
                    'foo': 'bar',
                    'label': None,
                },
            ),
            collision=dict(
                kwargs=dict(options=dict(execute='execute')),
                expected={
                    'net': None,
                    'link': None,
                    'stop-signal': None,
                    'restart': None,
                    'add-host': None,
                    'user': None,
                    'env': None,
                    'volume': None,
                    'publish': None,
                    'execute': 'execute',
                    'label': None,
                },
            ),
            override=dict(
                kwargs=dict(options=dict(env='custom_env')),
                expected={
                    'net': None,
                    'link': None,
                    'stop-signal': None,
                    'restart': None,
                    'add-host': None,
                    'user': None,
                    'env': 'custom_env',
                    'volume': None,
                    'publish': None,
                    'label': None,
                },
            ),
            complex=dict(
                kwargs=dict(options=dict(env='custom_env', foo='bar')),
                expected={
                    'net': None,
                    'link': None,
                    'stop-signal': None,
                    'restart': None,
                    'add-host': None,
                    'user': None,
                    'env': 'custom_env',
                    'volume': None,
                    'publish': None,
                    'foo': 'bar',
                    'label': None,
                },
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                container = TestContainer(**data['kwargs'])
                self.assertDictEqual(data['expected'], dict(container.options))

    def test_options_inheritance(self):

        class Parent(docker.Container):
            user = 'user'  # overridden property (simple)

            @property  # overridden property (dynamic)
            def ports(self):
                return 'ports'

            baz = Option(default=42)  # new property

            @Option  # new dynamic property
            def foo(self):
                return 'bar'

            @Option()  # new dynamic property
            def foo2(self):
                return 'bar2'

            @Option(default='not_used')  # new dynamic property
            def foo3(self):
                return 'bar3'

            null = Option()  # new empty property

            @Option(name='real-name')
            def alias(self):
                return 'value'

            @Option(name='real-name2')
            def overridden_alias(self):
                return 'value'

            @Option(name='real-name3')
            def overridden_alias2(self):
                return 'value'

        class Child(Parent):

            overridden_alias = 'overridden_value'

            @Option(name='overridden-name')
            def overridden_alias2(self):
                return 'overridden_value'

        container = Child()

        self.assertIn('user', container.options)
        self.assertEqual(container.options['user'], 'user')
        container.user = 'fabricio'
        self.assertEqual(container.options['user'], 'fabricio')

        self.assertIn('publish', container.options)
        self.assertEqual(container.options['publish'], 'ports')

        self.assertIn('baz', container.options)
        self.assertEqual(container.options['baz'], 42)
        container.baz = 101
        self.assertEqual(container.options['baz'], 101)

        self.assertIn('foo', container.options)
        self.assertEqual(container.options['foo'], 'bar')
        container.foo = 'baz'
        self.assertEqual(container.options['foo'], 'baz')

        self.assertIn('foo2', container.options)
        self.assertEqual(container.options['foo2'], 'bar2')
        container.foo2 = 'baz2'
        self.assertEqual(container.options['foo2'], 'baz2')

        self.assertIn('foo3', container.options)
        self.assertEqual(container.options['foo3'], 'bar3')
        container.foo3 = 'baz3'
        self.assertEqual(container.options['foo3'], 'baz3')

        self.assertIn('real-name', container.options)
        self.assertEqual(container.options['real-name'], 'value')
        container.alias = 'another_value'
        self.assertEqual(container.options['real-name'], 'another_value')

        self.assertIn('real-name2', container.options)
        self.assertEqual(container.options['real-name2'], 'overridden_value')
        container.overridden_alias = 'another_value'
        self.assertEqual(container.options['real-name2'], 'another_value')

        self.assertIn('overridden-name', container.options)
        self.assertEqual(container.options['overridden-name'], 'overridden_value')
        container.overridden_alias2 = 'another_value'
        self.assertEqual(container.options['overridden-name'], 'another_value')

        self.assertIn('null', container.options)
        self.assertIsNone(container.options['null'])
        container.null = 'value'
        self.assertEqual(container.options['null'], 'value')

    def test_attributes_inheritance(self):

        class Container(docker.Container):
            command = 'command'  # overridden property (simple)

            @property  # overridden property (dynamic)
            def stop_timeout(self):
                return 1001

            baz = Attribute(default=42)  # new property

            @Attribute  # new dynamic property
            def foo(self):
                return 'bar'

            @Attribute()  # new dynamic property
            def foo2(self):
                return 'bar2'

            @Attribute(default='not_used')  # new dynamic property
            def foo3(self):
                return 'bar3'

            null = Attribute()  # new empty property

        container = Container()

        self.assertEqual(container.command, 'command')
        container.command = 'command2'
        self.assertEqual(container.command, 'command2')

        self.assertEqual(container.stop_timeout, 1001)

        self.assertEqual(container.baz, 42)
        container.baz = 101
        self.assertEqual(container.baz, 101)

        self.assertEqual(container.foo, 'bar')
        container.foo = 'baz'
        self.assertEqual(container.foo, 'baz')

        self.assertEqual(container.foo2, 'bar2')
        container.foo2 = 'baz2'
        self.assertEqual(container.foo2, 'baz2')

        self.assertEqual(container.foo3, 'bar3')
        container.foo3 = 'baz3'
        self.assertEqual(container.foo3, 'baz3')

        self.assertIsNone(container.null)
        container.null = 'value'
        self.assertEqual(container.null, 'value')

    def test_container_does_not_allow_modify_options(self):
        container = TestContainer()

        # default options allowed to be modified
        container.user = 'user'
        self.assertEqual('user', container.user)

        # do not allow to modify additional options
        with self.assertRaises(TypeError):
            container.options['some-option'] = 'value'

    def test_container_raises_error_on_unknown_attr(self):
        with self.assertRaises(TypeError):
            docker.Container(name='name', unknown_attr='foo')

    def test_info(self):
        return_value = SucceededResult('[{"Id": "123", "Image": "abc"}]')
        expected = dict(Id='123', Image='abc')
        container = docker.Container(name='name')
        expected_command = 'docker inspect --type container name'
        with mock.patch.object(
            fabricio,
            'run',
            return_value=return_value,
        ) as run:
            self.assertEqual(expected, container.info)
            run.assert_called_once_with(
                expected_command,
                abort_exception=docker.ContainerNotFoundError,
            )

    def test_delete(self):
        cases = dict(
            regular=dict(
                delete_kwargs=dict(),
                expected_commands=[
                    mock.call('docker rm name'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                ],
            ),
            with_image=dict(
                delete_kwargs=dict(delete_image=True),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rm name'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                    mock.call('docker rmi image_id', ignore_errors=True),
                ],
            ),
            forced=dict(
                delete_kwargs=dict(force=True),
                expected_commands=[
                    mock.call('docker rm --force name'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                ],
            ),
            no_dangling_removal=dict(
                delete_kwargs=dict(delete_dangling_volumes=False),
                expected_commands=[
                    mock.call('docker rm name'),
                ],
            ),
            complex=dict(
                delete_kwargs=dict(force=True, delete_image=True),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rm --force name'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                    mock.call('docker rmi image_id', ignore_errors=True),
                ],
            ),
        )
        for case, params in cases.items():
            with self.subTest(case=case):
                container = docker.Container(name='name')
                with mock.patch.object(
                    fabricio,
                    'run',
                    return_value=SucceededResult('[{"Image": "image_id"}]'),
                ) as run:
                    expected_commands = params['expected_commands']
                    delete_kwargs = params['delete_kwargs']

                    container.delete(**delete_kwargs)
                    self.assertListEqual(run.mock_calls, expected_commands)

    def test_execute(self):
        container = docker.Container(name='name')
        expected_command = 'docker exec --tty --interactive name command'
        with mock.patch.object(
            fabricio,
            'run',
            return_value='result'
        ) as run:
            result = container.execute('command')
            run.assert_called_once_with(
                expected_command,
                ignore_errors=False,
                quiet=True,
                use_cache=False,
            )
            self.assertEqual('result', result)

    def test_start(self):
        container = docker.Container(name='name')
        expected_command = 'docker start name'
        with mock.patch.object(fabricio, 'run') as run:
            container.start()
            run.assert_called_once_with(expected_command)

    def test_stop(self):
        cases = dict(
            default=dict(
                timeout=None,
                expected_command='docker stop --time 10 name',
            ),
            positive_timeout=dict(
                timeout=30,
                expected_command='docker stop --time 30 name',
            ),
            zero_timeout=dict(
                timeout=0,
                expected_command='docker stop --time 0 name',
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                container = docker.Container(name='name')
                with mock.patch.object(fabricio, 'run') as run:
                    container.stop(timeout=data['timeout'])
                    run.assert_called_once_with(data['expected_command'])

    def test_restart(self):
        cases = dict(
            default=dict(
                timeout=None,
                expected_command='docker restart --time 10 name',
            ),
            positive_timeout=dict(
                timeout=30,
                expected_command='docker restart --time 30 name',
            ),
            zero_timeout=dict(
                timeout=0,
                expected_command='docker restart --time 0 name',
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                container = docker.Container(name='name')
                with mock.patch.object(fabricio, 'run') as run:
                    container.restart(timeout=data['timeout'])
                    run.assert_called_once_with(data['expected_command'])

    def test_rename(self):
        container = docker.Container(name='name')
        expected_command = 'docker rename name new_name'
        with mock.patch.object(fabricio, 'run') as run:
            container.rename('new_name')
            run.assert_called_once_with(expected_command)
            self.assertEqual('new_name', container.name)

    def test_signal(self):
        container = docker.Container(name='name')
        expected_command = 'docker kill --signal SIGTERM name'
        with mock.patch.object(fabricio, 'run') as run:
            container.signal('SIGTERM')
            run.assert_called_once_with(expected_command)

    def test_run(self):
        cases = dict(
            basic=dict(
                init_kwargs=dict(
                    name='name',
                ),
                class_kwargs=dict(image=docker.Image('image:tag')),
                expected_command='docker run --name name --detach image:tag ',
                expected_args={
                    'executable': ['docker', 'run'],
                    'name': 'name',
                    'detach': True,
                    'image': 'image:tag',
                    'command': [],
                },
            ),
            complex=dict(
                init_kwargs=dict(
                    name='name',
                    options={
                        'custom-option': 'foo',
                        'restart_policy': 'override',
                    },
                ),
                class_kwargs=dict(
                    image=docker.Image('image:tag'),
                    command='command',
                    user='user',
                    ports=['80:80', '443:443'],
                    env=['FOO=foo', 'BAR=bar'],
                    volumes=['/tmp:/tmp', '/root:/root:ro'],
                    links=['db:db'],
                    hosts=['host:192.168.0.1'],
                    network='network',
                    restart_policy='restart_policy',
                    stop_signal='stop_signal',
                ),
                expected_args={
                    'executable': ['docker', 'run'],
                    'user': 'user',
                    'publish': ['80:80', '443:443'],
                    'env': ['FOO=foo', 'BAR=bar'],
                    'volume': ['/tmp:/tmp', '/root:/root:ro'],
                    'link': ['db:db'],
                    'add-host': ['host:192.168.0.1'],
                    'net': 'network',
                    'restart': 'override',
                    'stop-signal': 'stop_signal',
                    'name': 'name',
                    'detach': True,
                    'custom-option': 'foo',
                    'image': 'image:tag',
                    'command': ['command'],
                },
            ),
        )

        def test_command(command, *args, **kwargs):
            options = docker_run_args_parser.parse_args(command.split())
            self.assertDictEqual(vars(options), params['expected_args'])
        for case, params in cases.items():
            with self.subTest(case=case):
                init_kwargs = params['init_kwargs']
                class_kwargs = params['class_kwargs']
                Container = type(docker.Container)(
                    'Container',
                    (docker.Container, ),
                    class_kwargs,
                )
                container = Container(**init_kwargs)
                with mock.patch.object(fabricio, 'run', side_effect=test_command):
                    container.run()

    def test_fork(self):
        cases = dict(
            default=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(),
                expected_properties=dict(
                    name='name',
                    command=None,
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': None,
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'label': None,
                    },
                ),
            ),
            predefined_default=dict(
                init_kwargs=dict(
                    name='name',
                    options=dict(user='fabricio', foo='baz'),
                    image='image:tag',
                    command='fab',
                ),
                fork_kwargs=dict(),
                expected_properties=dict(
                    name='name',
                    command='fab',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'fabricio',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'baz',
                        'label': None,
                    },
                ),
                expected_image='image:tag',
            ),
            override_name=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(name='another_name'),
                expected_properties=dict(
                    name='another_name',
                    command=None,
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': None,
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'label': None,
                    },
                ),
            ),
            override_command=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(command='command'),
                expected_properties=dict(
                    name='name',
                    command='command',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': None,
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'label': None,
                    },
                ),
            ),
            override_image_str=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(image='image'),
                expected_properties=dict(
                    name='name',
                    command=None,
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': None,
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'label': None,
                    },
                ),
                expected_image='image:latest',
            ),
            override_image_instance=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(image=docker.Image('image')),
                expected_properties=dict(
                    name='name',
                    command=None,
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': None,
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'label': None,
                    },
                ),
                expected_image='image:latest',
            ),
            override_default_option=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(options=dict(user='user')),
                expected_properties=dict(
                    name='name',
                    command=None,
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'user',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'label': None,
                    },
                ),
            ),
            override_custom_option=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(options=dict(foo='bar')),
                expected_properties=dict(
                    name='name',
                    command=None,
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': None,
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'bar',
                        'label': None,
                    },
                ),
            ),
            overrride_complex=dict(
                init_kwargs=dict(name='name'),
                fork_kwargs=dict(
                    options=dict(foo='bar', user='user'),
                    image='image',
                    command='command',
                    name='another_name',
                ),
                expected_properties=dict(
                    name='another_name',
                    command='command',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'user',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'bar',
                        'label': None,
                    },
                ),
                expected_image='image:latest',
            ),
            predefined_override_command=dict(
                init_kwargs=dict(
                    name='name',
                    options=dict(user='fabricio', foo='baz'),
                    image='image:tag',
                    command='fab',
                ),
                fork_kwargs=dict(command='command'),
                expected_properties=dict(
                    name='name',
                    command='command',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'fabricio',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'baz',
                        'label': None,
                    },
                ),
                expected_image='image:tag',
            ),
            predefined_override_image_str=dict(
                init_kwargs=dict(
                    name='name',
                    options=dict(user='fabricio', foo='baz'),
                    image='image:tag',
                    command='fab',
                ),
                fork_kwargs=dict(image='image'),
                expected_properties=dict(
                    name='name',
                    command='fab',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'fabricio',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'baz',
                        'label': None,
                    },
                ),
                expected_image='image:latest',
            ),
            predefined_override_image_instance=dict(
                init_kwargs=dict(
                    name='name',
                    options=dict(user='fabricio', foo='baz'),
                    image='image:tag',
                    command='fab',
                ),
                fork_kwargs=dict(image=docker.Image('image')),
                expected_properties=dict(
                    name='name',
                    command='fab',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'fabricio',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'baz',
                        'label': None,
                    },
                ),
                expected_image='image:latest',
            ),
            predefined_override_default_option=dict(
                init_kwargs=dict(
                    name='name',
                    options=dict(user='fabricio', foo='baz'),
                    image='image:tag',
                    command='fab',
                ),
                fork_kwargs=dict(options=dict(user='user')),
                expected_properties=dict(
                    name='name',
                    command='fab',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'user',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'baz',
                        'label': None,
                    },
                ),
                expected_image='image:tag',
            ),
            predefined_override_custom_option=dict(
                init_kwargs=dict(
                    name='name',
                    options=dict(user='fabricio', foo='baz'),
                    image='image:tag',
                    command='fab',
                ),
                fork_kwargs=dict(options=dict(foo='bar')),
                expected_properties=dict(
                    name='name',
                    command='fab',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'fabricio',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'bar',
                        'label': None,
                    },
                ),
                expected_image='image:tag',
            ),
            predefined_overrride_complex=dict(
                init_kwargs=dict(
                    name='name',
                    options=dict(user='fabricio', foo='baz', hello=42),
                    image='image:tag',
                    command='fab',
                ),
                fork_kwargs=dict(
                    options=dict(foo='bar', user='user'),
                    image='image',
                    command='command',
                    name='another_name',
                ),
                expected_properties=dict(
                    name='another_name',
                    command='command',
                    options={
                        'net': None,
                        'link': None,
                        'stop-signal': None,
                        'restart': None,
                        'add-host': None,
                        'user': 'user',
                        'env': None,
                        'volume': None,
                        'publish': None,
                        'foo': 'bar',
                        'hello': 42,
                        'label': None,
                    },
                ),
                expected_image='image:latest',
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                container = docker.Container(**data['init_kwargs'])
                forked_container = container.fork(**data['fork_kwargs'])
                expected_image = data.get('expected_image')
                if expected_image:
                    self.assertEqual(repr(forked_container.image), expected_image)
                for prop, value in data['expected_properties'].items():
                    self.assertEqual(value, getattr(forked_container, prop))

    @mock.patch.object(fabricio, 'log')
    def test_update(self, *args):
        cases = dict(
            no_change=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # current container info
                    SucceededResult('[{"Id": "image_id"}]'),  # new image info
                    SucceededResult(),  # force starting container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type image image:tag', abort_exception=docker.ImageNotFoundError),
                    mock.call('docker start name'),
                ],
                update_kwargs=dict(),
                excpected_result=False,
            ),
            no_change_with_tag=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # current container info
                    SucceededResult('[{"Id": "image_id"}]'),  # new image info
                    SucceededResult(),  # force starting container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type image image:foo', abort_exception=docker.ImageNotFoundError),
                    mock.call('docker start name'),
                ],
                update_kwargs=dict(tag='foo'),
                excpected_result=False,
            ),
            forced=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # obsolete container info
                    SucceededResult(),  # delete obsolete container
                    SucceededResult(),  # remove obsolete volumes
                    SucceededResult(),  # delete obsolete container image
                    SucceededResult(),  # rename current container
                    SucceededResult(),  # stop current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rm name_backup'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                    mock.call('docker rmi image_id', ignore_errors=True),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker stop --time 10 name_backup'),
                    mock.call('docker run --detach --name name image:tag ', quiet=True),
                ],
                update_kwargs=dict(force=True),
                excpected_result=True,
            ),
            regular=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # current container info
                    SucceededResult('[{"Id": "new_image_id"}]'),  # new image info
                    SucceededResult('[{"Image": "old_image_id"}]'),  # obsolete container info
                    SucceededResult(),  # delete obsolete container
                    SucceededResult(),  # remove obsolete volumes
                    SucceededResult(),  # delete obsolete container image
                    SucceededResult(),  # rename current container
                    SucceededResult(),  # stop current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type image image:tag', abort_exception=docker.ImageNotFoundError),
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rm name_backup'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                    mock.call('docker rmi old_image_id', ignore_errors=True),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker stop --time 10 name_backup'),
                    mock.call('docker run --detach --name name image:tag ', quiet=True),
                ],
                update_kwargs=dict(),
                excpected_result=True,
            ),
            regular_with_tag=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # current container info
                    SucceededResult('[{"Id": "new_image_id"}]'),  # new image info
                    SucceededResult('[{"Image": "old_image_id"}]'),  # obsolete container info
                    SucceededResult(),  # delete obsolete container
                    SucceededResult(),  # remove obsolete volumes
                    SucceededResult(),  # delete obsolete container image
                    SucceededResult(),  # rename current container
                    SucceededResult(),  # stop current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type image image:foo', abort_exception=docker.ImageNotFoundError),
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rm name_backup'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                    mock.call('docker rmi old_image_id', ignore_errors=True),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker stop --time 10 name_backup'),
                    mock.call('docker run --detach --name name image:foo ', quiet=True),
                ],
                update_kwargs=dict(tag='foo'),
                excpected_result=True,
            ),
            regular_with_registry=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # current container info
                    SucceededResult('[{"Id": "new_image_id"}]'),  # new image info
                    SucceededResult('[{"Image": "old_image_id"}]'),  # obsolete container info
                    SucceededResult(),  # delete obsolete container
                    SucceededResult(),  # remove obsolete volumes
                    SucceededResult(),  # delete obsolete container image
                    SucceededResult(),  # rename current container
                    SucceededResult(),  # stop current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type image registry/image:tag', abort_exception=docker.ImageNotFoundError),
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rm name_backup'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                    mock.call('docker rmi old_image_id', ignore_errors=True),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker stop --time 10 name_backup'),
                    mock.call('docker run --detach --name name registry/image:tag ', quiet=True),
                ],
                update_kwargs=dict(registry='registry'),
                excpected_result=True,
            ),
            regular_with_tag_and_registry=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # current container info
                    SucceededResult('[{"Id": "new_image_id"}]'),  # new image info
                    SucceededResult('[{"Image": "old_image_id"}]'),  # obsolete container info
                    SucceededResult(),  # delete obsolete container
                    SucceededResult(),  # remove obsolete volumes
                    SucceededResult(),  # delete obsolete container image
                    SucceededResult(),  # rename current container
                    SucceededResult(),  # stop current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type image registry/image:foo', abort_exception=docker.ImageNotFoundError),
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rm name_backup'),
                    mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
                    mock.call('docker rmi old_image_id', ignore_errors=True),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker stop --time 10 name_backup'),
                    mock.call('docker run --detach --name name registry/image:foo ', quiet=True),
                ],
                update_kwargs=dict(tag='foo', registry='registry'),
                excpected_result=True,
            ),
            regular_without_backup_container=dict(
                side_effect=(
                    SucceededResult('[{"Image": "image_id"}]'),  # current container info
                    SucceededResult('[{"Id": "new_image_id"}]'),  # new image info
                    docker.ContainerNotFoundError,  # obsolete container info
                    SucceededResult(),  # rename current container
                    SucceededResult(),  # stop current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type image image:tag', abort_exception=docker.ImageNotFoundError),
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker stop --time 10 name_backup'),
                    mock.call('docker run --detach --name name image:tag ', quiet=True),
                ],
                update_kwargs=dict(),
                excpected_result=True,
            ),
            forced_without_backup_container=dict(
                side_effect=(
                    docker.ContainerNotFoundError,  # obsolete container info
                    SucceededResult(),  # rename current container
                    SucceededResult(),  # stop current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker stop --time 10 name_backup'),
                    mock.call('docker run --detach --name name image:tag ', quiet=True),
                ],
                update_kwargs=dict(force=True),
                excpected_result=True,
            ),
            from_scratch=dict(
                side_effect=(
                    docker.ContainerNotFoundError,  # current container info
                    docker.ContainerNotFoundError,  # obsolete container info
                    RuntimeError,  # rename current container
                    SucceededResult('new_container_id'),  # run new container
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
                    mock.call('docker rename name name_backup'),
                    mock.call('docker run --detach --name name image:tag ', quiet=True),
                ],
                update_kwargs=dict(),
                excpected_result=True,
            ),
        )
        for case, params in cases.items():
            with self.subTest(case=case):
                container = TestContainer(name='name')
                side_effect = params['side_effect']
                expected_commands = params['expected_commands']
                update_kwargs = params['update_kwargs']
                excpected_result = params['excpected_result']
                with mock.patch.object(
                    fabricio,
                    'run',
                    side_effect=side_effect,
                ) as run:
                    result = container.update(**update_kwargs)
                    self.assertEqual('name', container.name)
                    self.assertListEqual(run.mock_calls, expected_commands)
                    self.assertEqual(excpected_result, result)

    def test_revert(self):
        side_effect = (
            SucceededResult('[{"Image": "backup_image_id"}]'),  # backup container info
            SucceededResult(),  # stop current container
            SucceededResult(),  # start backup container
            SucceededResult('[{"Image": "failed_image_id"}]'),  # current container info
            SucceededResult(),  # delete current container
            SucceededResult(),  # delete dangling volumes
            SucceededResult(),  # delete current container image
            SucceededResult(),  # rename backup container
        )
        expected_commands = [
            mock.call('docker inspect --type container name_backup', abort_exception=docker.ContainerNotFoundError),
            mock.call('docker stop --time 10 name'),
            mock.call('docker start name_backup'),
            mock.call('docker inspect --type container name', abort_exception=docker.ContainerNotFoundError),
            mock.call('docker rm name'),
            mock.call('for volume in $(docker volume ls --filter "dangling=true" --quiet); do docker volume rm "$volume"; done'),
            mock.call('docker rmi failed_image_id', ignore_errors=True),
            mock.call('docker rename name_backup name'),
        ]
        container = TestContainer(name='name')
        with mock.patch.object(fabricio, 'run', side_effect=side_effect) as run:
            container.revert()
            self.assertListEqual(run.mock_calls, expected_commands)

    @mock.patch.object(
        docker.Container,
        'info',
        new_callable=mock.PropertyMock,
        side_effect=docker.ContainerNotFoundError,
    )
    @mock.patch.object(fabricio, 'run')
    def test_revert_raises_error_if_backup_container_not_found(self, run, *args):
        container = docker.Container(name='name')
        with self.assertRaises(docker.ContainerNotFoundError):
            container.revert()
        run.assert_not_called()


class ImageTestCase(unittest.TestCase):

    @mock.patch.object(
        docker.Container,
        'info',
        new_callable=mock.PropertyMock,
        return_value={"Image": "image_id"},
    )
    def test_id(self, info):
        container = docker.Container(name='name', image='image:tag')
        image = container.image
        self.assertEqual(image.id, 'image_id')
        self.assertEqual(image.id, 'image_id')
        self.assertEqual(info.call_count, 1)

        self.assertEqual(container.image.id, 'image_id')
        self.assertEqual(info.call_count, 2)

    def test_info(self):
        return_value = SucceededResult('[{"Id": "123", "Image": "abc"}]')
        expected = dict(Id='123', Image='abc')
        image = docker.Image(name='name')
        expected_command = 'docker inspect --type image name:latest'
        with mock.patch.object(
            fabricio,
            'run',
            return_value=return_value,
        ) as run:
            self.assertEqual(expected, image.info)
            run.assert_called_once_with(
                expected_command,
                abort_exception=docker.ImageNotFoundError,
            )

    @mock.patch.object(fabricio, 'run', side_effect=RuntimeError)
    def test_info_raises_error_if_image_not_found(self, run):
        image = docker.Image(name='name')
        expected_command = 'docker inspect --type image name:latest'
        with self.assertRaises(RuntimeError):
            image.info
        run.assert_called_once_with(
            expected_command,
            abort_exception=docker.ImageNotFoundError,
        )

    def test_delete(self):
        cases = dict(
            default=dict(
                expeected_commands=[
                    mock.call('docker rmi image:latest', ignore_errors=True),
                ],
                kwargs=dict(),
            ),
            forced=dict(
                expeected_commands=[
                    mock.call('docker rmi --force image:latest', ignore_errors=True),
                ],
                kwargs=dict(force=True),
            ),
            do_not_ignore_errors=dict(
                expeected_commands=[
                    mock.call('docker rmi image:latest', ignore_errors=False),
                ],
                kwargs=dict(ignore_errors=False),
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                with mock.patch.object(fabricio, 'run') as run:
                    image = docker.Image('image')
                    image.delete(**data['kwargs'])
                    self.assertListEqual(
                        run.mock_calls,
                        data['expeected_commands'],
                    )

    def test_name_tag_registry(self):
        cases = dict(
            single=dict(
                init_kwargs=dict(
                    name='image',
                ),
                expected_name='image',
                expected_tag='latest',
                expected_registry=None,
                expected_str='image:latest',
            ),
            with_tag=dict(
                init_kwargs=dict(
                    name='image',
                    tag='tag',
                ),
                expected_name='image',
                expected_tag='tag',
                expected_registry=None,
                expected_str='image:tag',
            ),
            with_registry=dict(
                init_kwargs=dict(
                    name='image',
                    registry='registry:5000',
                ),
                expected_name='image',
                expected_tag='latest',
                expected_registry='registry:5000',
                expected_str='registry:5000/image:latest',
            ),
            with_tag_and_registry=dict(
                init_kwargs=dict(
                    name='image',
                    tag='tag',
                    registry='127.0.0.1:5000',
                ),
                expected_name='image',
                expected_tag='tag',
                expected_registry='127.0.0.1:5000',
                expected_str='127.0.0.1:5000/image:tag',
            ),
            with_tag_and_registry_and_user=dict(
                init_kwargs=dict(
                    name='user/image',
                    tag='tag',
                    registry='127.0.0.1:5000',
                ),
                expected_name='user/image',
                expected_tag='tag',
                expected_registry='127.0.0.1:5000',
                expected_str='127.0.0.1:5000/user/image:tag',
            ),
            single_arg_with_tag=dict(
                init_kwargs=dict(
                    name='image:tag',
                ),
                expected_name='image',
                expected_tag='tag',
                expected_registry=None,
                expected_str='image:tag',
            ),
            single_arg_with_registry=dict(
                init_kwargs=dict(
                    name='registry:123/image',
                ),
                expected_name='image',
                expected_tag='latest',
                expected_registry='registry:123',
                expected_str='registry:123/image:latest',
            ),
            single_arg_with_tag_and_registry=dict(
                init_kwargs=dict(
                    name='registry:123/image:tag',
                ),
                expected_name='image',
                expected_tag='tag',
                expected_registry='registry:123',
                expected_str='registry:123/image:tag',
            ),
            forced_with_tag=dict(
                init_kwargs=dict(
                    name='image:tag',
                    tag='foo',
                ),
                expected_name='image',
                expected_tag='foo',
                expected_registry=None,
                expected_str='image:foo',
            ),
            forced_with_registry=dict(
                init_kwargs=dict(
                    name='user/image',
                    registry='foo',
                ),
                expected_name='user/image',
                expected_tag='latest',
                expected_registry='foo',
                expected_str='foo/user/image:latest',
            ),
            forced_with_tag_and_registry=dict(
                init_kwargs=dict(
                    name='user/image:tag',
                    tag='foo',
                    registry='bar',
                ),
                expected_name='user/image',
                expected_tag='foo',
                expected_registry='bar',
                expected_str='bar/user/image:foo',
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                image = docker.Image(**data['init_kwargs'])
                self.assertEqual(data['expected_name'], image.name)
                self.assertEqual(data['expected_tag'], image.tag)
                self.assertEqual(data['expected_registry'], image.registry)
                self.assertEqual(data['expected_str'], str(image))

    def test_getitem(self):
        cases = dict(
            none=dict(
                item=None,
                expected_tag='tag',
                expected_registry='registry',
            ),
            tag=dict(
                item='custom_tag',
                expected_tag='custom_tag',
                expected_registry='registry',
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                image = docker.Image(name='name', tag='tag', registry='registry')
                new_image = image[data['item']]
                self.assertEqual(data['expected_tag'], new_image.tag)
                self.assertEqual(data['expected_registry'], new_image.registry)

    def test_getitem_slice(self):
        cases = dict(
            none=dict(
                start=None,
                stop=None,
                expected_tag='tag',
                expected_registry='registry',
            ),
            tag=dict(
                start=None,
                stop='custom_tag',
                expected_tag='custom_tag',
                expected_registry='registry',
            ),
            registry=dict(
                start='registry:5000',
                stop=None,
                expected_tag='tag',
                expected_registry='registry:5000',
            ),
            tag_and_registry=dict(
                start='127.0.0.1:5000',
                stop='custom_tag',
                expected_tag='custom_tag',
                expected_registry='127.0.0.1:5000',
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                image = docker.Image(name='name', tag='tag', registry='registry')
                new_image = image[data['start']:data['stop']]
                self.assertEqual(data['expected_tag'], new_image.tag)
                self.assertEqual(data['expected_registry'], new_image.registry)

    def test_run(self):
        image = docker.Image('image')
        cases = dict(
            default=dict(
                kwargs=dict(),
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'image': 'image:latest',
                    'command': [],
                },
            ),
            with_main_option=dict(
                kwargs=dict(options={'user': 'user'}),
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'user': 'user',
                    'image': 'image:latest',
                    'command': [],
                },
            ),
            with_additional_option=dict(
                kwargs=dict(options={'custom-option': 'bar'}),
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'custom-option': 'bar',
                    'image': 'image:latest',
                    'command': [],
                },
            ),
            with_main_option_deprecated=dict(
                kwargs=dict(user='user'),
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'user': 'user',
                    'image': 'image:latest',
                    'command': [],
                },
            ),
            with_additional_option_deprecated=dict(
                kwargs={'custom-option': 'bar'},
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'custom-option': 'bar',
                    'image': 'image:latest',
                    'command': [],
                },
            ),
            with_command=dict(
                kwargs=dict(command='command'),
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'image': 'image:latest',
                    'command': ['command'],
                },
            ),
            detached=dict(
                kwargs=dict(temporary=False, name='name'),
                expected_command='docker run --detach image:latest ',
                expected_args={
                    'executable': ['docker', 'run'],
                    'name': 'name',
                    'detach': True,
                    'image': 'image:latest',
                    'command': [],
                },
            ),
            with_name=dict(
                kwargs=dict(name='name'),
                expected_command='docker run --name name --rm --tty --interactive image:latest ',
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'image': 'image:latest',
                    'name': 'name',
                    'command': [],
                },
            ),
        )

        def test_command(command, *args, **kwargs):
            options = docker_run_args_parser.parse_args(command.split())
            self.assertDictEqual(vars(options), data['expected_args'])
        for case, data in cases.items():
            with self.subTest(case=case):
                with mock.patch.object(fabricio, 'run', side_effect=test_command):
                    image.run(**data['kwargs'])

    def test_image_as_descriptor(self):
        class Container(docker.Container):
            info = dict(Image='image_id')
        cases = dict(
            none=dict(
                image=None,
                expected_name=None,
                expected_registry=None,
                expected_tag=None,
            ),
            name=dict(
                image='image',
                expected_name='image',
                expected_registry=None,
                expected_tag='latest',
            ),
            name_and_tag=dict(
                image='image:tag',
                expected_name='image',
                expected_registry=None,
                expected_tag='tag',
            ),
            name_and_registry=dict(
                image='host:5000/image',
                expected_name='image',
                expected_registry='host:5000',
                expected_tag='latest',
            ),
            complex=dict(
                image='host:5000/user/image:tag',
                expected_name='user/image',
                expected_registry='host:5000',
                expected_tag='tag',
            ),
        )
        image = Container.image
        self.assertIsInstance(image, docker.Image)
        self.assertIsNone(image.name)
        self.assertIsNone(image.registry)
        self.assertIsNone(image.tag)
        self.assertIs(Container.image, image)
        for case, data in cases.items():
            with self.subTest(case=case):
                container = Container(image=data['image'])
                self.assertIs(container.image, container.image)
                self.assertIsInstance(container.image, docker.Image)
                self.assertEqual(container.image.name, data['expected_name'])
                self.assertEqual(container.image.registry, data['expected_registry'])
                self.assertEqual(container.image.tag, data['expected_tag'])
                self.assertEqual(container.image.id, 'image_id')

                container.image = old_image = container.image
                self.assertIsNot(container.image, old_image)
                self.assertIsInstance(container.image, docker.Image)
                self.assertEqual(container.image.name, data['expected_name'])
                self.assertEqual(container.image.registry, data['expected_registry'])
                self.assertEqual(container.image.tag, data['expected_tag'])
                self.assertEqual(container.image.id, 'image_id')

        for case, data in cases.items():
            with self.subTest(case='redefine_' + case):
                container = Container()
                container.image = data['image']
                self.assertIs(container.image, container.image)
                self.assertIsInstance(container.image, docker.Image)
                self.assertEqual(container.image.name, data['expected_name'])
                self.assertEqual(container.image.registry, data['expected_registry'])
                self.assertEqual(container.image.tag, data['expected_tag'])
                self.assertEqual(container.image.id, 'image_id')

                container.image = old_image = container.image
                self.assertIsNot(container.image, old_image)
                self.assertIsInstance(container.image, docker.Image)
                self.assertEqual(container.image.name, data['expected_name'])
                self.assertEqual(container.image.registry, data['expected_registry'])
                self.assertEqual(container.image.tag, data['expected_tag'])
                self.assertEqual(container.image.id, 'image_id')

        for case, data in cases.items():
            with self.subTest(case='predefined_' + case):
                Container.image = docker.Image(data['image'])
                container = Container()
                self.assertIs(container.image, container.image)
                self.assertIsInstance(container.image, docker.Image)
                self.assertEqual(container.image.name, data['expected_name'])
                self.assertEqual(container.image.registry, data['expected_registry'])
                self.assertEqual(container.image.tag, data['expected_tag'])
                self.assertEqual(container.image.id, 'image_id')

                container.image = old_image = container.image
                self.assertIsNot(container.image, old_image)
                self.assertIsInstance(container.image, docker.Image)
                self.assertEqual(container.image.name, data['expected_name'])
                self.assertEqual(container.image.registry, data['expected_registry'])
                self.assertEqual(container.image.tag, data['expected_tag'])
                self.assertEqual(container.image.id, 'image_id')

    def test_get_field_name_raises_error_on_collision(self):
        class Container(docker.Container):
            image2 = docker.Container.image
        container = Container(name='name')
        with self.assertRaises(ValueError):
            _ = container.image


class ServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.fab_settings = fab.settings(fab.hide('everything'))
        self.fab_settings.__enter__()

    def tearDown(self):
        fabricio.run.cache.clear()
        self.fab_settings.__exit__(None, None, None)

    def test_update(self, *args):
        cases = dict(
            worker=dict(
                init_kwargs=dict(
                    name='service',
                    image='image:tag',
                ),
                update_kwargs=dict(),
                side_effect=(
                    FailedResult(),
                ),
                args_parsers=[
                    docker_entity_inspect_args_parser,
                ],
                expected_args=[
                    {
                        'executable': ['docker', 'node', 'inspect'],
                        'format': "'{{.ManagerStatus.Leader}}'",
                        'service': 'self',
                    },
                ],
                expected_result=False,
                container_updated=None,
            ),
            not_changed=dict(
                init_kwargs=dict(
                    name='service',
                    image='image:tag',
                ),
                update_kwargs=dict(),
                side_effect=(
                    SucceededResult('false'),  # leader status
                    SucceededResult('[{}]'),  # service info
                    SucceededResult('[{"RepoDigests": ["digest"]}]'),  # image info
                ),
                args_parsers=[
                    docker_entity_inspect_args_parser,
                    docker_entity_inspect_args_parser,
                    docker_inspect_args_parser,
                ],
                expected_args=[
                    {
                        'executable': ['docker', 'node', 'inspect'],
                        'format': "'{{.ManagerStatus.Leader}}'",
                        'service': 'self',
                    },
                    {
                        'executable': ['docker', 'service', 'inspect'],
                        'service': 'service',
                    },
                    {
                        'executable': ['docker', 'inspect'],
                        'type': 'image',
                        'image_or_container': 'image:tag',
                    },
                ],
                expected_result=False,
                container_updated=False,
            ),
            not_leader=dict(
                init_kwargs=dict(
                    name='service',
                    image='image:tag',
                ),
                update_kwargs=dict(),
                side_effect=(
                    SucceededResult('false'),  # leader status
                    SucceededResult('[{}]'),  # service info
                    SucceededResult('[{"RepoDigests": ["digest"]}]'),  # image info
                ),
                args_parsers=[
                    docker_entity_inspect_args_parser,
                    docker_entity_inspect_args_parser,
                    docker_inspect_args_parser,
                ],
                expected_args=[
                    {
                        'executable': ['docker', 'node', 'inspect'],
                        'format': "'{{.ManagerStatus.Leader}}'",
                        'service': 'self',
                    },
                    {
                        'executable': ['docker', 'service', 'inspect'],
                        'service': 'service',
                    },
                    {
                        'executable': ['docker', 'inspect'],
                        'type': 'image',
                        'image_or_container': 'image:tag',
                    },
                ],
                expected_result=True,
                container_updated=True,
            ),
            updated=dict(
                init_kwargs=dict(
                    name='service',
                    image='image:tag',
                ),
                update_kwargs=dict(),
                side_effect=(
                    SucceededResult('true'),  # leader status
                    SucceededResult('[{"Spec": {}}]'),  # service info
                    SucceededResult('[{"RepoDigests": ["digest"]}]'),  # image info
                    SucceededResult(),  # service update
                ),
                args_parsers=[
                    docker_entity_inspect_args_parser,
                    docker_entity_inspect_args_parser,
                    docker_inspect_args_parser,
                    docker_service_update_args_parser,
                ],
                expected_args=[
                    {
                        'executable': ['docker', 'node', 'inspect'],
                        'format': "'{{.ManagerStatus.Leader}}'",
                        'service': 'self',
                    },
                    {
                        'executable': ['docker', 'service', 'inspect'],
                        'service': 'service',
                    },
                    {
                        'executable': ['docker', 'inspect'],
                        'type': 'image',
                        'image_or_container': 'image:tag',
                    },
                    {
                        'executable': ['docker', 'service', 'update'],
                        'image': 'digest',
                        'replicas': '1',
                        'service': 'service',
                    },
                ],
                expected_result=True,
                container_updated=True,
            ),
            created=dict(
                init_kwargs=dict(
                    name='service',
                    image='image:tag',
                ),
                update_kwargs=dict(),
                side_effect=(
                    SucceededResult('true'),  # leader status
                    docker.ServiceNotFoundError(),  # service info
                    SucceededResult('[{"RepoDigests": ["digest"]}]'),  # image info
                    SucceededResult(),  # service update
                ),
                args_parsers=[
                    docker_entity_inspect_args_parser,
                    docker_entity_inspect_args_parser,
                    docker_inspect_args_parser,
                    docker_service_create_args_parser,
                ],
                expected_args=[
                    {
                        'executable': ['docker', 'node', 'inspect'],
                        'format': "'{{.ManagerStatus.Leader}}'",
                        'service': 'self',
                    },
                    {
                        'executable': ['docker', 'service', 'inspect'],
                        'service': 'service',
                    },
                    {
                        'executable': ['docker', 'inspect'],
                        'type': 'image',
                        'image_or_container': 'image:tag',
                    },
                    {
                        'executable': ['docker', 'service', 'create'],
                        'image': ['image:tag'],
                        'name': 'service',
                        'replicas': '1',
                        'args': [],
                    },
                ],
                expected_result=True,
                container_updated=True,
            ),
        )

        def test_command(command, **kwargs):
            args = re.findall('".+?(?<!\\\\)"|\'.+?(?<!\\\\)\'|[^\s]+', command)
            parser = next(args_parsers)
            options = parser.parse_args(args)
            self.assertDictEqual(vars(options), next(expected_args))
            result = next(side_effect)
            if isinstance(result, Exception):
                raise result
            return result
        for case, data in cases.items():
            expected_args = iter(data['expected_args'])
            args_parsers = iter(data['args_parsers'])
            side_effect = iter(data['side_effect'])
            with self.subTest(case=case):
                fabricio.run.cache.clear()
                with mock.patch.object(fab, 'run', side_effect=test_command) as run:
                    run.__name__ = 'mocked_run'
                    with mock.patch.object(docker.Container, 'update', return_value=data['container_updated']):
                        service = docker.Service(**data['init_kwargs'])
                        result = service.update(**data['update_kwargs'])
                        self.assertEqual(result, data['expected_result'])
                        self.assertEqual(run.call_count, len(data['expected_args']))

    def test_update_full_cycle(self):
        pass  # TODO without container mock

    def test_create_full_cycle(self):
        pass  # TODO without container mock

    @mock.patch.object(docker.Image, 'digest', new_callable=mock.PropertyMock)
    @mock.patch.object(fabricio, 'run', return_value=SucceededResult('[{}]'))
    def test_update_options_removes_info_after_evaluating(self, *args):
        service = docker.Service(name='service')
        self.assertIsInstance(service.update_options, collections.Mapping)
        self.assertNotIn('info', service.__dict__)

    def test_update_options(self, *args):
        cases = dict(
            default=dict(
                init_kwargs=dict(name='name'),
                service_info=dict(),
                expected={
                    'env-add': None,
                    'constraint-add': None,
                    'label-rm': None,
                    'network': None,
                    'env-rm': None,
                    'publish-add': None,
                    'label-add': None,
                    'args': None,
                    'mount-rm': None,
                    'container-label-rm': None,
                    'user': None,
                    'replicas': 1,
                    'publish-rm': None,
                    'mount-add': None,
                    'constraint-rm': None,
                    'stop-grace-period': None,
                    'restart-condition': None,
                    'container-label-add': None,
                },
            ),
            empty_args=dict(
                init_kwargs=dict(name='name', args=''),
                service_info=dict(),
                expected={
                    'env-add': None,
                    'constraint-add': None,
                    'label-rm': None,
                    'network': None,
                    'env-rm': None,
                    'publish-add': None,
                    'label-add': None,
                    'args': '',
                    'mount-rm': None,
                    'container-label-rm': None,
                    'user': None,
                    'replicas': 1,
                    'publish-rm': None,
                    'mount-add': None,
                    'constraint-rm': None,
                    'stop-grace-period': None,
                    'restart-condition': None,
                    'container-label-add': None,
                },
            ),
            new_option_value=dict(
                init_kwargs=dict(
                    name='service',
                    args='arg1 "arg2" \'arg3\'',
                    options=dict(
                        ports='source:target',
                        mounts='type=volume,destination=/path',
                        labels='label=value',
                        env='FOO=bar',
                        constraints='node.role == manager',
                        container_labels='label=value',
                        network='network',
                        restart_condition='on-failure',
                        stop_timeout=10,
                        custom_option='custom_value',
                        replicas=3,
                        user='user',
                    ),
                ),
                service_info=dict(),
                expected={
                    'env-add': 'FOO=bar',
                    'constraint-add': 'node.role == manager',
                    'label-rm': None,
                    'network': None,
                    'env-rm': None,
                    'publish-add': 'source:target',
                    'label-add': 'label=value',
                    'args': 'arg1 "arg2" \'arg3\'',
                    'mount-rm': None,
                    'container-label-rm': None,
                    'user': 'user',
                    'replicas': 3,
                    'publish-rm': None,
                    'mount-add': 'type=volume,destination=/path',
                    'constraint-rm': None,
                    'stop-grace-period': 10,
                    'restart-condition': 'on-failure',
                    'custom_option': 'custom_value',
                    'container-label-add': 'label=value',
                },
            ),
            new_option_value_by_sentinel=dict(
                init_kwargs=dict(
                    name='service',
                    sentinel=docker.Container(
                        stop_timeout=20,
                        options=dict(
                            user='user',
                            ports='source:target',
                            env='FOO=bar',

                            volumes='volumes',
                            links='links',
                            hosts='hosts',
                            network='network',
                            restart_policy='restart_policy',
                            stop_signal='INT',
                            custom_option='custom_value',
                        ),
                    ),
                ),
                service_info=dict(),
                expected={
                    "env-add": "FOO=bar",
                    "constraint-add": None,
                    "label-rm": None,
                    "network": None,
                    "env-rm": None,
                    "publish-add": "source:target",
                    "label-add": None,
                    "args": None,
                    "mount-rm": None,
                    "container-label-rm": None,
                    "user": "user",
                    "replicas": 1,
                    "publish-rm": None,
                    "mount-add": None,
                    "constraint-rm": None,
                    "stop-grace-period": 20,
                    "restart-condition": None,
                    "container-label-add": None
                },
            ),
            new_option_value_by_sentinel_override=dict(
                init_kwargs=dict(
                    name='service',
                    sentinel=docker.Container(
                        name='container',
                        stop_timeout=20,
                        options=dict(
                            user='user',
                            ports='source:target',
                            env='FOO=bar',

                            volumes='volumes',
                            links='links',
                            hosts='hosts',
                            network='network',
                            restart_policy='restart_policy',
                            stop_signal='INT',
                            custom_option='custom_value',
                        ),
                    ),
                    options=dict(
                        stop_timeout=30,
                        user='service',
                        ports='80:80',
                        env='BAR=baz',
                    ),
                ),
                service_info=dict(),
                expected={
                    "env-add": "BAR=baz",
                    "constraint-add": None,
                    "label-rm": None,
                    "network": None,
                    "env-rm": None,
                    "publish-add": "80:80",
                    "label-add": None,
                    "args": None,
                    "mount-rm": None,
                    "container-label-rm": None,
                    "user": "service",
                    "replicas": 1,
                    "publish-rm": None,
                    "mount-add": None,
                    "constraint-rm": None,
                    "stop-grace-period": 30,
                    "restart-condition": None,
                    "container-label-add": None
                },
            ),
            new_options_values=dict(
                init_kwargs=dict(
                    name='service',
                    options=dict(
                        ports=[
                            'source:target',
                            'source2:target2',
                        ],
                        mounts=[
                            'type=volume,destination=/path',
                            'type=volume,destination="/path2"',
                        ],
                        labels=[
                            'label=value',
                            'label2=value2',
                        ],
                        container_labels=[
                            'label=value',
                            'label2=value2',
                        ],
                        constraints=[
                            'node.role == manager',
                            'node.role == worker',
                        ],
                        env=[
                            'FOO=bar',
                            'FOO2=bar2',
                        ],
                    ),
                ),
                service_info=dict(),
                expected={
                    'env-add': ['FOO=bar', 'FOO2=bar2'],
                    'constraint-add': ['node.role == manager', 'node.role == worker'],
                    'label-rm': None,
                    'network': None,
                    'env-rm': None,
                    'publish-add': ['source:target', 'source2:target2'],
                    'label-add': ['label=value', 'label2=value2'],
                    'args': None,
                    'mount-rm': None,
                    'container-label-rm': None,
                    'user': None,
                    'replicas': 1,
                    'publish-rm': None,
                    'mount-add': ['type=volume,destination=/path', 'type=volume,destination="/path2"'],
                    'constraint-rm': None,
                    'stop-grace-period': None,
                    'restart-condition': None,
                    'container-label-add': ['label=value', 'label2=value2'],
                },
            ),
            remove_option_value=dict(
                init_kwargs=dict(
                    name='service',
                ),
                service_info=dict(
                    Spec=dict(
                        Labels=dict(
                            label='value',
                        ),
                        TaskTemplate=dict(
                            ContainerSpec=dict(
                                Labels=dict(
                                    label='value',
                                ),
                                Env=[
                                    'FOO=bar',
                                ],
                                Mounts=[
                                    dict(
                                        Type='volume',
                                        Source='/source',
                                        Target='/path',
                                    ),
                                ]
                            ),
                            Placement=dict(
                                Constraints=[
                                    'node.role == manager',
                                ],
                            ),
                        ),
                        EndpointSpec=dict(
                            Ports=[
                                dict(
                                    TargetPort='target',
                                    Protocol='tcp',
                                    PublishedPort='source',
                                ),
                            ],
                        ),
                    ),
                ),
                expected={
                    'env-add': None,
                    'constraint-add': None,
                    'label-rm': set(['label']),
                    'network': None,
                    'env-rm': set(['FOO=bar']),
                    'publish-add': None,
                    'label-add': None,
                    'args': None,
                    'mount-rm': set(['/path']),
                    'container-label-rm': set(['label']),
                    'user': None,
                    'replicas': 1,
                    'publish-rm': set(['target']),
                    'mount-add': None,
                    'constraint-rm': set(['node.role == manager']),
                    'stop-grace-period': None,
                    'restart-condition': None,
                    'container-label-add': None,
                },
            ),
            remove_single_option_value_from_two=dict(
                init_kwargs=dict(
                    name='service',
                    options=dict(
                        ports='source2:target2',
                        mounts='type=volume,destination=/path',
                        labels='label=value',
                        env='FOO=bar',
                        constraints='node.role == manager',
                        container_labels='label=value',
                    ),
                ),
                service_info=dict(
                    Spec=dict(
                        Labels=dict(
                            label='value',
                            label2='value2',
                        ),
                        TaskTemplate=dict(
                            ContainerSpec=dict(
                                Labels=dict(
                                    label='value',
                                    label2='value2',
                                ),
                                Env=[
                                    'FOO=bar',
                                    'FOO2=bar2',
                                ],
                                Mounts=[
                                    dict(
                                        Type='volume',
                                        Source='/source',
                                        Target='/path',
                                    ),
                                    dict(
                                        Type='volume',
                                        Source='/source2',
                                        Target='/path2',
                                    ),
                                ]
                            ),
                            Placement=dict(
                                Constraints=[
                                    'node.role == manager',
                                    'node.role == worker',
                                ],
                            ),
                        ),
                        EndpointSpec=dict(
                            Ports=[
                                dict(
                                    TargetPort='target',
                                    Protocol='tcp',
                                    PublishedPort='source',
                                ),
                                dict(
                                    TargetPort='target2',
                                    Protocol='tcp',
                                    PublishedPort='source2',
                                ),
                            ],
                        ),
                    ),
                ),
                expected={
                    'env-add': 'FOO=bar',
                    'constraint-add': 'node.role == manager',
                    'label-rm': set(['label2']),
                    'network': None,
                    'env-rm': set(['FOO2=bar2']),
                    'publish-add': 'source2:target2',
                    'label-add': 'label=value',
                    'args': None,
                    'mount-rm': set(['/path2']),
                    'container-label-rm': set(['label2']),
                    'user': None,
                    'replicas': 1,
                    'publish-rm': set(['target']),
                    'mount-add': 'type=volume,destination=/path',
                    'constraint-rm': set(['node.role == worker']),
                    'stop-grace-period': None,
                    'restart-condition': None,
                    'container-label-add': 'label=value',
                },
            ),
            remove_single_option_value_from_three=dict(
                init_kwargs=dict(
                    name='service',
                    options=dict(
                        ports=[
                            'source2:target2',
                            'source3:target3',
                        ],
                        mounts=[
                            'type=volume,destination=/path',
                            'type=volume,destination="/path2"',
                        ],
                        labels=[
                            'label=value',
                            'label2=value2',
                        ],
                        env=[
                            'FOO=bar',
                            'FOO2=bar2',
                        ],
                        constraints=[
                            'node.role == manager',
                            'node.role == worker',
                        ],
                        container_labels=[
                            'label=value',
                            'label2=value2',
                        ],
                    ),
                ),
                service_info=dict(
                    Spec=dict(
                        Labels=dict(
                            label='value',
                            label2='value2',
                            label3='value3',
                        ),
                        TaskTemplate=dict(
                            ContainerSpec=dict(
                                Labels=dict(
                                    label='value',
                                    label2='value2',
                                    label3='value3',
                                ),
                                Env=[
                                    'FOO=bar',
                                    'FOO2=bar2',
                                    'FOO3=bar3',
                                ],
                                Mounts=[
                                    dict(
                                        Type='volume',
                                        Source='/source',
                                        Target='/path',
                                    ),
                                    dict(
                                        Type='volume',
                                        Source='/source2',
                                        Target='/path2',
                                    ),
                                    dict(
                                        Type='volume',
                                        Source='/source3',
                                        Target='/path3',
                                    ),
                                ]
                            ),
                            Placement=dict(
                                Constraints=[
                                    'node.role == manager',
                                    'node.role == worker',
                                    'constraint',
                                ],
                            ),
                        ),
                        EndpointSpec=dict(
                            Ports=[
                                dict(
                                    TargetPort='target',
                                    Protocol='tcp',
                                    PublishedPort='source',
                                ),
                                dict(
                                    TargetPort='target2',
                                    Protocol='tcp',
                                    PublishedPort='source2',
                                ),
                                dict(
                                    TargetPort='target3',
                                    Protocol='tcp',
                                    PublishedPort='source3',
                                ),
                            ],
                        ),
                    ),
                ),
                expected={
                    'env-add': ['FOO=bar', 'FOO2=bar2'],
                    'constraint-add': ['node.role == manager', 'node.role == worker'],
                    'label-rm': set(['label3']),
                    'network': None,
                    'env-rm': set(['FOO3=bar3']),
                    'publish-add': ['source2:target2', 'source3:target3'],
                    'label-add': ['label=value', 'label2=value2'],
                    'args': None,
                    'mount-rm': set(['/path3']),
                    'container-label-rm': set(['label3']),
                    'user': None,
                    'replicas': 1,
                    'publish-rm': set(['target']),
                    'mount-add': ['type=volume,destination=/path', 'type=volume,destination="/path2"'],
                    'constraint-rm': set(['constraint']),
                    'stop-grace-period': None,
                    'restart-condition': None,
                    'container-label-add': ['label=value', 'label2=value2'],
                },
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                with mock.patch.object(
                    docker.Service,
                    'info',
                    new_callable=mock.PropertyMock,
                    return_value=data['service_info'],
                    __delete__=lambda *_: None,
                ):
                    service = docker.Service(**data['init_kwargs'])
                    self.assertDictEqual(
                        dict(service.update_options),
                        data['expected'],
                    )

    def test__sentinel_set_service_options(self):
        cases = dict(
            empty=dict(
                service_init_kwargs=dict(),
                update_options='',
                expected_sentinel_labels=['_service_options=""'],
            ),
            default=dict(
                service_init_kwargs=dict(),
                update_options='--replicas 1 --image registry/user/image@digest',
                expected_sentinel_labels=['_service_options="--replicas 1 --image registry/user/image@digest"'],
            ),
            update_options_with_quotes=dict(
                service_init_kwargs=dict(),
                update_options='--replicas 1 --image image --foo "bar baz"',
                expected_sentinel_labels=['_service_options="--replicas 1 --image image --foo \\"bar baz\\""'],
            ),
            unicode_update_options=dict(
                service_init_kwargs=dict(),
                update_options=u'--replicas 1 --image image --foo фу',
                expected_sentinel_labels=['_service_options="--replicas 1 --image image --foo \\u0444\\u0443"'],
            ),
            existing_label=dict(
                service_init_kwargs=dict(sentinel=docker.Container(options=dict(labels='label'))),
                update_options='--replicas 1 --image image',
                expected_sentinel_labels=[
                    'label',
                    '_service_options="--replicas 1 --image image"',
                ],
            ),
            existing_labels=dict(
                service_init_kwargs=dict(sentinel=docker.Container(options=dict(labels=['label1', 'label2']))),
                update_options='--replicas 1 --image image',
                expected_sentinel_labels=[
                    'label1',
                    'label2',
                    '_service_options="--replicas 1 --image image"',
                ],
            ),
            existing_unicode_labels=dict(
                service_init_kwargs=dict(sentinel=docker.Container(options=dict(labels=[u'фу', u'бар']))),
                update_options='--replicas 1 --image image',
                expected_sentinel_labels=[
                    u'фу',
                    u'бар',
                    '_service_options="--replicas 1 --image image"',
                ],
            ),
            existing_unicode_label_as_object=dict(
                service_init_kwargs=dict(sentinel=docker.Container(options=dict(labels=docker.Container(name=u'фу')))),
                update_options='--replicas 1 --image image',
                expected_sentinel_labels=[
                    u'фу',
                    '_service_options="--replicas 1 --image image"',
                ],
            ),
            empty_list_of_labels=dict(
                service_init_kwargs=dict(sentinel=docker.Container(options=dict(labels=[]))),
                update_options='--replicas 1 --image image',
                expected_sentinel_labels=['_service_options="--replicas 1 --image image"'],
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                service = docker.Service(**data['service_init_kwargs'])
                old_labels_id = id(service.sentinel.labels)
                service._sentinel_set_service_options(data['update_options'])
                self.assertEqual(
                    service.sentinel.labels,
                    data['expected_sentinel_labels'],
                )
                self.assertNotEqual(id(service.sentinel.labels), old_labels_id)
