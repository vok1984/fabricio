import argparse


class SucceededResult(str):

    succeeded = True

    failed = False


class FailedResult(str):

    succeeded = False

    failed = True

docker_run_args_parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
docker_run_args_parser.add_argument('executable', nargs=2)
docker_run_args_parser.add_argument('--user')
docker_run_args_parser.add_argument('--publish', action='append')
docker_run_args_parser.add_argument('--env', action='append')
docker_run_args_parser.add_argument('--volume', action='append')
docker_run_args_parser.add_argument('--link', action='append')
docker_run_args_parser.add_argument('--add-host', action='append', dest='add-host')
docker_run_args_parser.add_argument('--net')
docker_run_args_parser.add_argument('--restart')
docker_run_args_parser.add_argument('--stop-signal', dest='stop-signal')
docker_run_args_parser.add_argument('--detach', action='store_true')
docker_run_args_parser.add_argument('--tty', action='store_true')
docker_run_args_parser.add_argument('--interactive', action='store_true')
docker_run_args_parser.add_argument('--rm', action='store_true')
docker_run_args_parser.add_argument('--name')
docker_run_args_parser.add_argument('--custom-option', dest='custom-option')
docker_run_args_parser.add_argument('image')
docker_run_args_parser.add_argument('command', nargs=argparse.REMAINDER)

docker_service_update_args_parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
docker_service_update_args_parser.add_argument('executable', nargs=3)
docker_service_update_args_parser.add_argument('--env-add', dest='env-add', action='append')
docker_service_update_args_parser.add_argument('--env-rm', dest='env-rm', action='append')
docker_service_update_args_parser.add_argument('--image')
docker_service_update_args_parser.add_argument('--mount-add', dest='mount-add', action='append')
docker_service_update_args_parser.add_argument('--mount-rm', dest='mount-rm', action='append')
docker_service_update_args_parser.add_argument('--name')
docker_service_update_args_parser.add_argument('--publish-add', dest='publish-add', action='append')
docker_service_update_args_parser.add_argument('--publish-rm', dest='publish-rm', action='append')
docker_service_update_args_parser.add_argument('--label-add', dest='label-add', action='append')
docker_service_update_args_parser.add_argument('--label-rm', dest='label-rm', action='append')
docker_service_update_args_parser.add_argument('--constraint-add', dest='constraint-add', action='append')
docker_service_update_args_parser.add_argument('--constraint-rm', dest='constraint-rm', action='append')
docker_service_update_args_parser.add_argument('--container-label-add', dest='container-label-add', action='append')
docker_service_update_args_parser.add_argument('--container-label-rm', dest='container-label-rm', action='append')
docker_service_update_args_parser.add_argument('--replicas')
docker_service_update_args_parser.add_argument('--restart-condition', dest='restart-condition')
docker_service_update_args_parser.add_argument('--user')
docker_service_update_args_parser.add_argument('--args')
docker_service_update_args_parser.add_argument('--custom-option', dest='custom-option')
docker_service_update_args_parser.add_argument('service')

args_parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
args_parser.add_argument('args', nargs=argparse.REMAINDER)
