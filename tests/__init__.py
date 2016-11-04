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

args_parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
args_parser.add_argument('args', nargs=argparse.REMAINDER)
