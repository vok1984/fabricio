import itertools

from cached_property import cached_property

from fabricio import docker, utils


class Migration(str):

    def split_migration(self):
        app, _, name = self.partition('.')
        return app, name

    @cached_property
    def app(self):
        app, self.name = self.split_migration()
        return app

    @cached_property
    def name(self):
        self.app, name = self.split_migration()
        return name


class DjangoContainer(docker.Container):
    """
    Be sure you use proper Dockerfile's WORKDIR directive
    (or another alternative) which points to the directory where
    manage.py placed
    """

    def migrate(self, tag=None, registry=None):
        self.image[registry:tag].run(
            'python manage.py migrate --noinput',
            quiet=False,
            options=self.safe_options,
        )

    @staticmethod
    def _get_parent_migration(migration, migrations):
        migrations = iter(migrations)
        any(migration == m for m in migrations)  # skip later migrations
        for parent_migration in migrations:
            if migration.app == parent_migration.app:
                return parent_migration
        return Migration(migration.app + '.zero')

    def get_revert_migrations(self, current_migrations, backup_migrations):
        current_migrations, all_migrations = itertools.tee(reversed(map(
            Migration,
            current_migrations.splitlines(),
        )))
        all_migrations = list(all_migrations)

        backup_migrations = reversed(map(
            Migration,
            backup_migrations.splitlines(),
        ))

        revert_migrations = utils.OrderedDict()

        while True:
            backup_migration = next(backup_migrations, None)
            for current_migration in current_migrations:
                if current_migration == backup_migration:
                    break
                revert_migrations[current_migration.app] = self._get_parent_migration(
                    current_migration,
                    migrations=all_migrations,
                )

            if backup_migration is None:
                return revert_migrations.values()

    def migrate_back(self):
        migrations_command = 'python manage.py showmigrations --plan | egrep "^\[X\]" | awk "{print \$2}"'

        backup_container = self.get_backup_container()
        options = self.safe_options

        current_migrations = self.image.run(
            command=migrations_command,
            options=options,
        )
        backup_migrations = backup_container.image.run(
            command=migrations_command,
            options=options,
        )
        revert_migrations = self.get_revert_migrations(
            current_migrations,
            backup_migrations,
        )

        for migration in revert_migrations:
            command = 'python manage.py migrate --no-input {app} {migration}'.format(
                app=migration.app,
                migration=migration.name,
            )
            self.image.run(command=command, quiet=False, options=options)
