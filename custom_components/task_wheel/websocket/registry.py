"""Alle Befehle der Panel-API an einer Stelle (ohne Home Assistant)."""

from typing import Final

from . import actions, config, read
from .command import Command

COMMANDS: Final[tuple[Command, ...]] = (*read.COMMANDS, *actions.COMMANDS, *config.COMMANDS)
