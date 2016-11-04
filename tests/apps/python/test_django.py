import mock
import unittest2 as unittest

from fabric import api as fab

import fabricio

from fabricio import docker
from fabricio.apps.python.django import DjangoContainer
from tests import SucceededResult, docker_run_args_parser, args_parser


class DjangoContainerTestCase(unittest.TestCase):

    def test_migrate(self):
        cases = dict(
            new_migrations=dict(
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'image': 'image:tag',
                    'command': ['python', 'manage.py', 'migrate', '--noinput'],
                },
                kwargs=dict(),
                container_class_vars=dict(name='name'),
            ),
            customized=dict(
                expected_args={
                    'executable': ['docker', 'run'],
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'image': 'registry/image:foo',
                    'command': ['python', 'manage.py', 'migrate', '--noinput'],
                },
                kwargs=dict(tag='foo', registry='registry'),
                container_class_vars=dict(name='name'),
            ),
            default_with_customized_container=dict(
                expected_args={
                    'executable': ['docker', 'run'],
                    'user': 'user',
                    'env': ['env'],
                    'volume': ['volumes'],
                    'link': ['links'],
                    'add-host': ['hosts'],
                    'net': 'network',
                    'restart': 'restart_policy',
                    'stop-signal': 'stop_signal',
                    'rm': True,
                    'tty': True,
                    'interactive': True,
                    'image': 'image:tag',
                    'command': ['python', 'manage.py', 'migrate', '--noinput'],
                },
                kwargs=dict(),
                container_class_vars=dict(
                    user='user',
                    env='env',
                    volumes='volumes',
                    links='links',
                    hosts='hosts',
                    network='network',
                    command='command',
                    restart_policy='restart_policy',
                    stop_signal='stop_signal',
                    stop_timeout='stop_timeout',

                    ports='ports',
                ),
            ),
        )

        def test_command(command, *args, **kwargs):
            options = docker_run_args_parser.parse_args(command.split())
            self.assertDictEqual(vars(options), data['expected_args'])
        for case, data in cases.items():
            with self.subTest(case=case):
                with mock.patch.object(fabricio, 'run', side_effect=test_command):
                    TestContainer = type(
                        'TestContainer',
                        (DjangoContainer, ),
                        dict(
                            dict(image=docker.Image('image:tag')),
                            **data['container_class_vars']
                        ),
                    )
                    container = TestContainer('test')
                    with fab.settings(fab.hide('everything')):
                        container.migrate(**data['kwargs'])

    def test_migrate_back(self):
        cases = dict(
            no_change=dict(
                side_effect=iter((
                    SucceededResult('[{"Image": "current_image_id"}]'),
                    SucceededResult(
                        'app1.0001_initial\n'
                        'app1.0002_foo\n'
                        'app2.0001_initial\n'
                    ),
                    SucceededResult('[{"Image": "backup_image_id"}]'),
                    SucceededResult(
                        'app1.0001_initial\n'
                        'app1.0002_foo\n'
                        'app2.0001_initial\n'
                    ),
                )),
                expected_args=iter([
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name_backup'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'backup_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                ]),
            ),
            no_migrations=dict(
                side_effect=iter((
                    SucceededResult('[{"Image": "current_image_id"}]'),
                    SucceededResult(),
                    SucceededResult('[{"Image": "backup_image_id"}]'),
                    SucceededResult(),
                )),
                expected_args=iter([
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name_backup'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'backup_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                ]),
            ),
            regular=dict(
                side_effect=iter((
                    SucceededResult('[{"Image": "current_image_id"}]'),
                    SucceededResult(
                        'app0.0001_initial\n'
                        'app1.0001_initial\n'
                        'app1.0002_foo\n'
                        'app2.0001_initial\n'
                        'app3.0001_initial\n'
                        'app2.0002_foo\n'
                        'app3.0002_foo\n'
                    ),
                    SucceededResult('[{"Image": "backup_image_id"}]'),
                    SucceededResult(
                        'app1.0001_initial\n'
                        'app1.0002_foo\n'
                        'app2.0001_initial\n'
                    ),
                    SucceededResult(),
                    SucceededResult(),
                    SucceededResult(),
                )),
                expected_args=iter([
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name_backup'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'backup_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'migrate', '--no-input', 'app3', 'zero'],
                    }),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'migrate', '--no-input', 'app2', '0001_initial'],
                    }),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'migrate', '--no-input', 'app0', 'zero'],
                    }),
                ]),
            ),
            with_container_custom_options=dict(
                side_effect=iter((
                    SucceededResult('[{"Image": "current_image_id"}]'),
                    SucceededResult(
                        'app0.0001_initial\n'
                        'app1.0001_initial\n'
                        'app1.0002_foo\n'
                        'app2.0001_initial\n'
                        'app3.0001_initial\n'
                        'app2.0002_foo\n'
                        'app3.0002_foo\n'
                    ),
                    SucceededResult('[{"Image": "backup_image_id"}]'),
                    SucceededResult(
                        'app1.0001_initial\n'
                        'app1.0002_foo\n'
                        'app2.0001_initial\n'
                    ),
                    SucceededResult(),
                    SucceededResult(),
                    SucceededResult(),
                )),
                expected_args=iter([
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'user': 'user',
                        'env': ['env'],
                        'volume': ['volumes'],
                        'link': ['links'],
                        'add-host': ['hosts'],
                        'net': 'network',
                        'restart': 'restart_policy',
                        'stop-signal': 'stop_signal',
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                    (args_parser, dict(args=['docker', 'inspect', '--type', 'container', 'name_backup'])),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'user': 'user',
                        'env': ['env'],
                        'volume': ['volumes'],
                        'link': ['links'],
                        'add-host': ['hosts'],
                        'net': 'network',
                        'restart': 'restart_policy',
                        'stop-signal': 'stop_signal',
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'backup_image_id',
                        'command': ['python', 'manage.py', 'showmigrations', '--plan', '|', 'egrep', '"^\\[X\\]"', '|', 'awk', '"{print', '\\$2}"'],
                    }),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'user': 'user',
                        'env': ['env'],
                        'volume': ['volumes'],
                        'link': ['links'],
                        'add-host': ['hosts'],
                        'net': 'network',
                        'restart': 'restart_policy',
                        'stop-signal': 'stop_signal',
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'migrate', '--no-input', 'app3', 'zero'],
                    }),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'user': 'user',
                        'env': ['env'],
                        'volume': ['volumes'],
                        'link': ['links'],
                        'add-host': ['hosts'],
                        'net': 'network',
                        'restart': 'restart_policy',
                        'stop-signal': 'stop_signal',
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'migrate', '--no-input', 'app2', '0001_initial'],
                    }),
                    (docker_run_args_parser, {
                        'executable': ['docker', 'run'],
                        'user': 'user',
                        'env': ['env'],
                        'volume': ['volumes'],
                        'link': ['links'],
                        'add-host': ['hosts'],
                        'net': 'network',
                        'restart': 'restart_policy',
                        'stop-signal': 'stop_signal',
                        'rm': True,
                        'tty': True,
                        'interactive': True,
                        'image': 'current_image_id',
                        'command': ['python', 'manage.py', 'migrate', '--no-input', 'app0', 'zero'],
                    }),
                ]),
                init_kwargs=dict(
                    options=dict(
                        user='user',
                        env='env',
                        volumes='volumes',
                        links='links',
                        hosts='hosts',
                        network='network',
                        restart_policy='restart_policy',
                        stop_signal='stop_signal',

                        ports='ports',
                    ),
                    command='command',
                    stop_timeout='stop_timeout',
                ),
            ),
        )

        def test_command(command, *args, **kwargs):
            parser, expected_args = next(data['expected_args'])
            options = parser.parse_args(command.split())
            self.assertDictEqual(vars(options), expected_args)
            return next(data['side_effect'])
        for case, data in cases.items():
            with self.subTest(case=case):
                with mock.patch.object(
                    fabricio,
                    'run',
                    side_effect=test_command,
                ):
                    container = DjangoContainer(
                        name='name',
                        image='image:tag',
                        **data.get('init_kwargs', {})
                    )
                    container.migrate_back()

    def test_migrate_back_errors(self):
        cases = dict(
            current_container_not_found=dict(
                expected_exception=RuntimeError,
                expected_error_message="Container 'name' not found",
                side_effect=(
                    RuntimeError,
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name'),
                ],
            ),
            backup_container_not_found=dict(
                expected_exception=RuntimeError,
                expected_error_message="Container 'name_backup' not found",
                side_effect=(
                    SucceededResult('[{"Image": "current_image_id"}]'),
                    SucceededResult(
                        'app1.0001_initial\n'
                    ),
                    RuntimeError,
                ),
                expected_commands=[
                    mock.call('docker inspect --type container name'),
                    mock.call('docker run --rm --tty --interactive current_image_id python manage.py showmigrations --plan | egrep "^\[X\]" | awk "{print \$2}"', quiet=True),
                    mock.call('docker inspect --type container name_backup'),
                ],
            ),
        )
        for case, data in cases.items():
            with self.subTest(case=case):
                with mock.patch.object(
                    fabricio,
                    'run',
                    side_effect=data['side_effect'],
                ) as run:
                    expected_commands = data['expected_commands']
                    container = DjangoContainer(name='name', image='image')
                    with self.assertRaises(data['expected_exception']) as cm:
                        container.migrate_back()
                    self.assertEqual(
                        cm.exception.args[0],
                        data['expected_error_message'],
                    )
                    self.assertListEqual(run.mock_calls, expected_commands)
