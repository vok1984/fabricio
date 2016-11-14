import hashlib
import sys

from fabric import colors, api as fab

from fabricio import utils

fab.env.setdefault('infrastructure', None)


def _command(
    fabric_method,
    command,
    ignore_errors=False,
    quiet=True,
    hide=('running', ),
    show=(),
    **kwargs
):
    if quiet:
        hide += ('output', 'warnings')
    log('{method}: {command}'.format(
        method=fabric_method.__name__,
        command=command,
    ))
    with fab.settings(fab.hide(*hide), fab.show(*show), warn_only=True):
        result = fabric_method(command, **kwargs)
        if not ignore_errors and result.failed:
            raise RuntimeError(result)
    return result


def run(
    command,
    sudo=False,
    stdout=sys.stdout,
    stderr=sys.stderr,
    use_cache=False,
    cache_key='',
    **kwargs
):
    if use_cache:
        md5 = hashlib.md5()
        md5.update(command)
        md5.update(fab.env.host or '')
        md5.update(cache_key)
        cache_key = md5.digest()
        if cache_key in run.cache:
            return run.cache[cache_key]
    fabric_method = sudo and fab.sudo or fab.run
    result = _command(
        fabric_method=fabric_method,
        command=command,
        stdout=stdout,
        stderr=stderr,
        **kwargs
    )
    if use_cache:
        run.cache[cache_key] = result
    return result
run.cache = {}


def local(command, use_cache=False, **kwargs):
    if use_cache:
        md5 = hashlib.md5()
        md5.update(command)
        cache_key = md5.digest()
        if cache_key in local.cache:
            return local.cache[cache_key]
    result = _command(
        fabric_method=fab.local,
        command=command,
        **kwargs
    )
    if use_cache:
        local.cache[cache_key] = result
    return result
local.cache = {}


def log(message, color=colors.yellow, output=sys.stdout):
    with utils.patch(sys, 'stdout', output):
        fab.puts(color(message))


def move(path_from, path_to, sudo=False, ignore_errors=False):
    return run(
        'mv {path_from} {path_to}'.format(
            path_from=path_from,
            path_to=path_to,
        ),
        sudo=sudo,
        ignore_errors=ignore_errors,
    )


def remove(path, sudo=False, force=True, ignore_errors=False):
    return run(
        'rm {force}{path}'.format(
            force=force and '-f ' or '',
            path=path,
        ),
        sudo=sudo,
        ignore_errors=ignore_errors,
    )
