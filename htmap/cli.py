import logging
import sys
import random

import htmap

import click
from click_didyoumean import DYMGroup
from halo import Halo
from spinners import Spinners

spinners = list(name for name in Spinners.__members__ if 'dots' in name)


def make_spinner(*args, **kwargs):
    return Halo(
        *args,
        spinner = random.choice(spinners),
        stream = sys.stderr,
        **kwargs,
    )


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CONTEXT_SETTINGS = dict(help_option_names = ['-h', '--help'])


def _read_ids_from_stdin(ctx, param, value):
    if not value and not click.get_text_stream('stdin').isatty():
        return click.get_text_stream('stdin').read().split()
    else:
        return value


@click.group(context_settings = CONTEXT_SETTINGS, cls = DYMGroup)
@click.option(
    '--verbose', '-v',
    is_flag = True,
    default = False,
    help = 'Show log messages as the CLI runs.',
)
def cli(verbose):
    """HTMap command line tools."""
    htmap.settings['CLI'] = True
    if verbose:
        _start_htmap_logger()


def _start_htmap_logger():
    htmap_logger = logging.getLogger('htmap')
    htmap_logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(stream = sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    htmap_logger.addHandler(handler)

    return handler


@cli.command()
def ids():
    """Print map ids. Suitable for piping to other commands."""
    click.echo(_id_list())


@cli.command()
@click.option(
    '--no-state',
    is_flag = True,
    default = False,
    help = 'Do not show map component states.',
)
@click.option(
    '--no-meta',
    is_flag = True,
    default = False,
    help = 'Do not show map metadata (memory, runtime, etc.).',
)
def status(no_state, no_meta):
    """Print the status of all maps."""
    maps = htmap.load_maps()
    if not no_state:
        with make_spinner(text = 'Reading map component statuses...') as spinner:
            for map in maps:
                map.status_counts  # force maps to read event logs in advance
            spinner.succeed()

    msg = htmap.status(maps, state = not no_state, meta = not no_meta)

    click.echo(msg)


@cli.command()
@click.option(
    '--yes',
    is_flag = True,
    default = False,
    help = 'Do not ask for confirmation.',
)
@click.option(
    '--force',
    is_flag = True,
    default = False,
    help = 'Do a force-clean instead of a normal clean.',
)
def clean(yes, force):
    """Remove all maps."""
    if not yes:
        click.secho(
            'Are you sure you want to delete all of your maps permanently?'
            '\nThis action cannot be undone!'
            '\nType YES to delete all of your maps: ',
            fg = 'red',
        )
        answer = input()
    else:
        answer = 'YES'

    if answer == 'YES':
        if not force:
            htmap.clean()
        else:
            htmap.force_clean()
    else:
        click.echo('Answer was not YES, maps have not been deleted.')


@cli.command()
@click.argument(
    'ids',
    nargs = -1,
    callback = _read_ids_from_stdin,
    required = False,
)
def wait(ids):
    """Wait for maps to complete."""
    for map_id in ids:
        _cli_load(map_id).wait(show_progress_bar = True)


@cli.command()
@click.argument(
    'ids',
    nargs = -1,
    callback = _read_ids_from_stdin,
    required = False,
)
@click.option(
    '--force',
    is_flag = True,
    default = False,
    help = 'Do a force-remove instead of a normal remove.',
)
def remove(ids, force):
    """Remove maps."""
    for map_id in ids:
        if not force:
            _cli_load(map_id).remove()
        else:
            htmap.force_remove(map_id)


@cli.command()
@click.argument(
    'ids',
    nargs = -1,
    callback = _read_ids_from_stdin,
    required = False,
)
def release(ids):
    """Release maps."""
    for map_id in ids:
        _cli_load(map_id).release()


@cli.command()
@click.argument(
    'ids',
    nargs = -1,
    callback = _read_ids_from_stdin,
    required = False,
)
def hold(ids):
    """Hold maps."""
    for map_id in ids:
        _cli_load(map_id).hold()


@cli.command()
@click.argument(
    'ids',
    nargs = -1,
    callback = _read_ids_from_stdin,
    required = False,
)
def reasons(ids):
    """Print the hold reasons for maps."""
    for map_id in ids:
        click.echo(_cli_load(map_id).hold_report())


@cli.command()
@click.argument('id')
@click.argument('newid')
def rename(id, newid):
    """Rename a map."""
    _cli_load(id).rename(newid)


@cli.command()
def version():
    """Print HTMap version information."""
    click.echo(htmap.version())


def _cli_load(map_id) -> htmap.Map:
    with make_spinner(text = f'Loading map {map_id}...') as spinner:
        try:
            return htmap.load(map_id)
        except Exception as e:
            spinner.fail(f'Error: could not find a map with map_id {map_id}')
            click.echo(f'Your map ids are:')
            click.echo(_id_list())

            sys.exit(1)


def _id_list() -> str:
    return '\n'.join(htmap.map_ids())
