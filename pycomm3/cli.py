import typer
import logging

from typing import Optional

from ._version import __version__
from .logger import LOG_VERBOSE, configure_default_logger
from .cip_driver import CIPDriver

from typer import Option, Argument
from collections import defaultdict


app = typer.Typer(
    name="pycomm3",
    no_args_is_help=True,
)


_LOGGING_LEVELS = defaultdict(
    int,
    {
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
        4: LOG_VERBOSE,
    },
)

state = {"log_level": 0}


def _version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def app_callback(
    verbose: int = Option(0, "--verbose", "-v", count=True, max=4, clamp=True),
    log_file: str = Option(None, "--log", "-l"),
    version: Optional[bool] = Option(
        None, "--version", "-V", is_eager=True, callback=_version_callback
    ),
):

    """
    DOC
    """
    log_level = _LOGGING_LEVELS[verbose]
    if log_level:
        configure_default_logger(level=log_level, filename=log_file)


@app.command()
def discover(
    format: str = Option(
        "{ip_address: <15}: {product_name}",
        help="format string used to print each device",
    )
):
    """
    To change how each discovered device is returned, use the --format option.
    Variables available include any that are in the Identity Object dict
    returned by the CIPDriver.discover() method.  Refer to the documentation for
    more details.
    """
    try:
        results = CIPDriver.discover()
        if results:
            for result in results:
                typer.echo(format.format(**result))
    except Exception as err:
        typer.echo(f"Error discovering devices: {err!r}")
