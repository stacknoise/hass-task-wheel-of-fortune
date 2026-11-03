"""Was nach der Auslösung eines einmaligen Zeitplans mit ihm geschieht (Tabelle)."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from types import MappingProxyType

from ..enums import AfterOnce
from ..models import ManualTrigger, OnceTrigger, Schedule

type AfterAction = Callable[[Schedule], Schedule | None]

# `None` heißt: Zeitplan löschen
_AFTER_ACTIONS: Mapping[AfterOnce, AfterAction] = MappingProxyType(
    {
        AfterOnce.KEEP_MANUAL: lambda schedule: replace(schedule, trigger=ManualTrigger()),
        AfterOnce.ARCHIVE: lambda schedule: replace(schedule, enabled=False, archived=True),
        AfterOnce.DELETE: lambda _schedule: None,
    }
)


def after_fired(schedule: Schedule) -> Schedule | None:
    """Zeitplan nach der automatischen Auslösung: behalten, archiviert oder `None` (löschen).

    Zeitpläne anderer Arten bleiben unverändert.
    """
    trigger = schedule.trigger
    if not isinstance(trigger, OnceTrigger):
        return schedule
    return _AFTER_ACTIONS[trigger.after](schedule)
