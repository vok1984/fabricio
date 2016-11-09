from fabricio import tasks, docker
from fabricio.misc import AvailableVagrantHosts

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
