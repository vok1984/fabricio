from fabricio import tasks, docker
from fabricio.misc import AvailableVagrantHosts

my_nginx = tasks.ImageBuildDockerTasks(
    service=docker.Container(
        name='my_nginx',
        image='my_nginx',
        options=dict(
            ports='80:80',
        ),
    ),
    hosts=AvailableVagrantHosts(),
    registry='localhost:5000',
)
