import re

from cached_property import cached_property
from fabric import api as fab


class AvailableVagrantHosts(object):
    """
    Returns list of IP addresses of available vagrant VMs in the current dir.

    If provided network_interface then use it to fetch IP within guest machine.
    """

    def __init__(self, network_interface=None):
        self.guest_network_interface = network_interface

    def __iter__(self):
        return iter(self.hosts)

    def _get_ip(self, host_string):
        with fab.settings(
            host_string=host_string,
            # see https://github.com/fabric/fabric/issues/1522
            # disable_known_hosts=True,
        ):
            ip_command = (
                "ip addr show {interface} "
                "| grep 'inet ' "
                "| head -1 "
                "| awk '{{ print $2 }}'"
            ).format(interface=self.guest_network_interface)
            ip = fab.run(
                ip_command,
                quiet=True,
            ).split('/')[0]
            if not ip:
                error_msg = 'Could not find IPV4 address of ' + host_string
                raise ValueError(error_msg)
            return ip

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
            if self.guest_network_interface is not None:
                ip = self._get_ip(host_string)
                host_string = '{User}@{ip}'.format(ip=ip, **ssh_config)
            fab.puts('Added host: ' + host_string)
            hosts.append(host_string)
        return hosts