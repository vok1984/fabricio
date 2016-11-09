from fabricio import tasks
from fabricio.apps.db.postgres import StreamingReplicatedPostgresqlContainer
from fabricio.misc import AvailableVagrantHosts

db = tasks.DockerTasks(
    service=StreamingReplicatedPostgresqlContainer(
        name='postgres',
        image='postgres:9.6',
        pg_data='/data',
        pg_recovery_master_promotion_enabled=True,
        options=dict(
            volumes='/data:/data',
            env='PGDATA=/data',
            ports='5432:5432',
        ),
    ),
    hosts=AvailableVagrantHosts(network_interface='eth1'),
)
