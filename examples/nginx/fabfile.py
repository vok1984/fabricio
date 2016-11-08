import re

from cached_property import cached_property
from fabric import api as fab
from fabricio import tasks, docker


class AvailableVagrantHosts(object):

    def __iter__(self):
        return iter(self.hosts)

    @cached_property
    def hosts(self):
        keys = fab.env.key_filename = []
        hosts = []
        fab.local('vagrant up')
        ssh_configs_data = fab.local('vagrant ssh-config', capture=True)
        ssh_configs = map(
            lambda config: dict(map(
                lambda row: row.lstrip().split(' ', 1),
                config.splitlines()
            )),
            re.split('(?m)\s*^$\s*', ssh_configs_data),
        )
        for ssh_config in ssh_configs:
            keys.append(ssh_config['IdentityFile'])
            host_string = '{User}@{HostName}:{Port}'.format(**ssh_config)
            with fab.settings(
                host_string=host_string,
                # see https://github.com/fabric/fabric/issues/1522
                # disable_known_hosts=True,
            ):
                ip_command = (
                    "ip addr show eth1 "
                    "| grep inet "
                    "| head -1 "
                    "| awk '{ print $2 }'"
                )
                ip = ssh_config['Host'] = fab.run(
                    ip_command,
                    quiet=True,
                ).split('/')[0]
                if not ip:
                    error_msg = 'Could not find IP address of ' + host_string
                    raise ValueError(error_msg)
            host = '{User}@{Host}'.format(**ssh_config)
            fab.puts('Added host: ' + host)
            hosts.append(host)
        return hosts


nginx = tasks.DockerTasks(
    service=docker.Container(
        name='nginx',
        image='nginx:stable',
        options=dict(
            ports='80:80',
        ),
    ),
    hosts=AvailableVagrantHosts(),
)

my_nginx = tasks.BuildDockerTasks(
    service=docker.Container(
        name='my_nginx',
        image='my_nginx',
        options=dict(
            ports='8000:80',
        ),
    ),
    hosts=AvailableVagrantHosts(),
)
