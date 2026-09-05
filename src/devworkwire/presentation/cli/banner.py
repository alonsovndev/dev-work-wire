"""Renders the CLI's startup banner: logo, tagline, and author/version legend."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

import pyfiglet
import typer

_LOGO_TEXT = "DWIRE"
_LOGO_FONT = "ansi_shadow"
_TAGLINE = "Jira Backlog Automation Assistant"
_AUTHOR = "alonsovndev"


def app_version() -> str:
    """Installed ``devworkwire`` version, or a dev placeholder when not installed."""
    try:
        return _pkg_version("devworkwire")
    except PackageNotFoundError:
        return "0.0.0-dev"


def render_box() -> str:
    """The bordered logo + tagline block, as a single multi-line string."""
    logo_lines = pyfiglet.figlet_format(_LOGO_TEXT, font=_LOGO_FONT).rstrip("\n").splitlines()
    content_width = max(len(line) for line in [*logo_lines, _TAGLINE, "DevWorkWire"])

    def row(text: str = "") -> str:
        return f"║  {text.ljust(content_width)}  ║"

    lines = ["╔" + "═" * (content_width + 4) + "╗"]
    lines += [row(line) for line in logo_lines]
    lines.append(row("DevWorkWire"))
    lines.append(row(_TAGLINE))
    lines.append("╚" + "═" * (content_width + 4) + "╝")
    return "\n".join(lines)


def render_legend() -> str:
    """One-line "developed by / version" footer shown below the box."""
    return f"Developed by {_AUTHOR} · v{app_version()}"


def print_banner() -> None:
    typer.secho(render_box(), fg=typer.colors.CYAN)
    typer.echo()
    typer.secho(render_legend(), fg=typer.colors.BRIGHT_BLACK)
    typer.echo()
    typer.echo("System ready.")
